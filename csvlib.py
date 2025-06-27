import csv 
from functools import cmp_to_key

def is_float(n):
    try:
        return float(n) != None
    except ValueError:
        return False


class Stats(object):
    def __init__(self, tool):
        self.SAFE = 'TRUE'
        self.UNSAFE = 'FALSE'
        self.TIMEOUT = 'TIMEOUT'
        self.OOM = 'OOM'
        self.UNKNOWN = 'UNKNOWN'

        self.tool = tool 
        
        # stats about answers
        self.num_unknowns = 0
        self.num_timeouts = 0
        self.num_ooms = 0
        self.num_safe_answers = 0
        self.num_unsafe_answers = 0 

        # stats about ground-truth
        self.total_time = 0.0 # time it takes overall to run benchmarks e2e, regardless of result
        self.time_safe = 0.0 # time it takes across all safe benchmarks, regardless of result
        self.time_unsafe = 0.0 # time it takes across all unsafe benchmarks, regardless of result

        self.total_safe_benchmarks = 0
        self.total_unsafe_benchmarks = 0
   
        self.rows = []


    def add_row(self, result):
        (name, ground_truth, answer, walltime) = (None, None, None, None)
        print(self.tool.name, result)
        if is_float(result[2]):
            name = result[0]
            ground_truth = self.UNSAFE
            answer = self.determine_answer(result[1])
            walltime = float(result[3])
        else:
            name = result[0]
            ground_truth = self.determine_answer(result[1])
            answer = self.determine_answer(result[2])
            walltime = float(result[4])
            #print('answer: ', answer, 'result[2]', result[2])
#print(result)
        assert name != None
        assert ground_truth != None
        assert answer != None
        assert walltime != None
        self.rows.append({'name': name, 'ground_truth': ground_truth, 'answer': answer, 'time': walltime })
        self.total_time += walltime
        #print('row: ', self.rows[-1])
        if ground_truth == self.SAFE:
            self.time_safe += walltime
            self.total_safe_benchmarks += 1 
        else:
            assert ground_truth == self.UNSAFE and ground_truth
            self.time_unsafe += walltime
            self.total_unsafe_benchmarks += 1

        if answer == self.UNKNOWN:
            self.num_unknowns += 1 
        if answer == self.OOM:
            self.num_ooms += 1
        if answer == self.TIMEOUT:
            self.num_timeouts += 1
        if answer == self.SAFE:
            self.num_safe_answers += 1
        if answer == self.UNSAFE:
            self.num_unsafe_answers += 1

    def determine_answer(self, s):
        if 'KILL' in s:
            return self.OOM
        elif 'OUT OF MEM' in s:
            return self.OOM
        elif ('unknown' in s) or ('EXCEPTION' in s):
            return self.UNKNOWN
        elif 'TIMEOUT' in s:
            return self.TIMEOUT
        elif 'true' in s:
            return self.SAFE
        elif 'false' in s:
            return self.UNSAFE
        else:
            print('ERROR: ', s)
            exit(1)

    def getrow(self, name):
        for x in self.rows:
            if x['name'] == name:
                return x

    def solved_benchmarks(self):
        safe = []
        unsafe = []
        for x in self.rows:
            if x['answer'] == self.SAFE:
                safe.append(x['name'])
            if x['answer'] == self.UNSAFE:
                unsafe.append(x['name'])
        return safe, unsafe

    # (correct, timeout, oom, unknown)
    def get_scatter_row(self, name):
        x = self.getrow(name)
#print(x, name)
        if x['answer'] in [self.SAFE, self.UNSAFE]:
            # ToolName, time_correct, time_timeout, time_oom, time_unknown
            return (self.tool.name, x['time'], '*', '*', '*')
        elif x['answer'] == self.TIMEOUT:
            return (self.tool.name, '*', x['time'], '*', '*')
        elif x['answer'] == self.OOM:
            return (self.tool.name, '*', '*', x['time'], '*')
        else:
            assert x['answer'] == self.UNKNOWN
            return (self.tool.name, '*', '*', '*', x['time'])

    def print(self):
        total_benchmarks = self.total_safe_benchmarks+self.total_unsafe_benchmarks
        total_correct_answers = self.num_safe_answers+self.num_unsafe_answers
        print(f'Tool: {self.tool.name}')
        print('---------------------------------------')
        print('Type\t#tasks\t#correct\ttime')
        print(f'all\t{total_benchmarks}\t{total_correct_answers}\t{self.total_time}')
        print(f'safe\t{self.total_safe_benchmarks}\t{self.num_safe_answers}\t{self.time_safe}')
        print(f'unsafe\t{self.total_unsafe_benchmarks}\t{self.num_unsafe_answers}\t{self.time_unsafe}')
        print(f'Failures (Timeout/Memout/Unknowns): ({self.num_timeouts}/{self.num_ooms}/{self.num_unknowns})')
        print('---------------------------------------')

    def print_benchmarks(self, cmp):
        rs = sorted(self.rows, cmp_to_key(cmp))
        for x in rs:
            print(x['name'], x['ground_truth'], x['answer'], x['time'])


    def __str__(self):
        return '\n'.join(list(map(lambda x: str(x), self.rows)))


class Tool(object):

    def __init__(self, name, csvfiles):
        self.name = name
        self.csvfiles = csvfiles
        self.read()

    def read(self):
        IDX_START = 3
        self.content = []
        for csvfile in self.csvfiles:
            with open(csvfile, 'r') as file:
                csv_reader = csv.reader(file,delimiter='\t')
                rows = []
                for row in csv_reader:
                    if len(row)==0:
                        continue
                    rows.append(row)
                self.content += (rows[IDX_START:])
            
    def benchmarks(self):
        return list(map(lambda x: x[0], self.content))

    def stats(self):
        st = Stats(self)
        for bench in self.content:
            st.add_row(bench)
        return st

    def stats_starting_with(self, pref):
        st = Stats(self)
        for bench in self.content:
            if bench[0].startswith(pref):
                st.add_row(bench)
        return st

    def __str__(self):
        stats = self.stats()
        return self.name + '\n' + str(stats)


class ToolCollection(object):
    def __init__(self):
        self.tools = []

    def add_tool(self, tool):
        self.tools.append(tool)

    def same_benchmarks(self, ground_truth):
        t0 = set(ground_truth)
        for tool in self.tools:
            t1 = set(tool.benchmarks())
            if t1 != t0:
                return (False, tool, t1.symmetric_difference(t0))
        return (True, set())


def make_diagram(solved_safe, solved_unsafe):
    # Venn4 using venny4py

    for tool in solved_safe:
        solved_safe[tool] = set(solved_safe[tool])
        print('total solved for ', tool, ' : ', len(solved_safe[tool]) + len(solved_unsafe[tool]))
        print('num safe, solved for ', tool, ' : ', len(solved_safe[tool]))
    for tool in solved_unsafe:
        solved_unsafe[tool] = set(solved_unsafe[tool])
        print('num unsafe, solved for ', tool, ' : ', len(solved_unsafe[tool]))

    venny4py(sets=solved_safe,out='safe_venn4',ext='pdf')
    venny4py(sets=solved_unsafe,out='unsafe_venn4',ext='pdf')
    print('done, output in safe_venn4/ , unsafe_venn4/')



def scatter_v2(toolstats, benchmarks):
    scatter = {}
    for tool in toolstats:
        scatter[tool] = []
    for bench in benchmarks:
        for tool in toolstats:
            result = toolstats[tool].get_scatter_row(bench)
            if result[1] != '*':
                scatter[tool].append(float(result[1]))
    for tool in toolstats:
        scatter[tool] = sorted(scatter[tool])
    s = """\\begin{tikzpicture}
            \\begin{axis}[
            xlabel={Benchmarks},
            ylabel={\# Solved},
            title=Intraprocedural Benchmarks,
            grid=both,
            tick align = outside,
            yticklabel style={/pgf/number format/fixed},     
            scaled x ticks = false,
            xticklabel style={/pgf/number format/fixed},
            legend style={at={(1.05,1)}, anchor=north west}
            ]
            """
    print(s)
    s = "%"
    for tool in toolstats:
        print(f"%%%%%%  {tool} ")
        print('\\addplot+[] coordinates {') # only marks
        for i in range(len(scatter[tool])):
            print(f'({i}, {scatter[tool][i]})') 
        print('};')
        print('\\addlegendentry{' + str(tool)+'};')

    print('\\end{axis}')
    print("\\end{tikzpicture}")
            

def to_stream(stats, benchmarks, csvs):
    streams = {}
    for bench in stats:
        streams[bench] = {}
        order = []
        for tool in csvs:
            order.append(tool)
        inds = sorted(benchmarks[bench])
        for tool in order:
            streams[bench][tool] = {}
            streams[bench][tool]['OK'] = []
            streams[bench][tool]['TLE'] = []
            streams[bench][tool]['OOM'] = []
            streams[bench][tool]['UNK'] = []
            streams[bench][tool]['ALL'] = []
            for idx in inds:
                row = stats[bench][idx][tool]
    #print(row)
                if row[0] != '*':
                    streams[bench][tool]['OK'].append((idx, row[0]))
                    streams[bench][tool]['ALL'].append((idx, row[0]))
                if row[1] != '*':
                    pass
                    streams[bench][tool]['TLE'].append((idx, row[1]))
                    streams[bench][tool]['ALL'].append((idx, row[1]))
                if row[2] != '*':
                    streams[bench][tool]['OOM'].append((idx,row[2]))
                    streams[bench][tool]['ALL'].append((idx,row[2]))
                if row[3] != '*':
                    streams[bench][tool]['UNK'].append((idx,row[3]))
                    streams[bench][tool]['ALL'].append((idx,row[3]))


def scatter_v1(stats, benchmarks, keyword, csvs):
    streams = to_stream(stats, benchmarks)

    for bench in streams:
        if keyword == None or keyword in bench:
            s = """\\begin{tikzpicture}
            \\begin{axis}[
            xlabel={$N$},
            ylabel={Time (s)},
            title={""" + bench + """},
            grid=both,
            tick align = outside,
            yticklabel style={/pgf/number format/fixed},     
            scaled x ticks = false,
            xticklabel style={/pgf/number format/fixed},
            legend style={at={(1.05,1)}, anchor=north west}
            ]
            """
            print(s)
            for tool in streams[bench]:
                        print(f'% {tool}, {bench}')
                        print('\\addplot+[] coordinates {') # only marks
                        for line in streams[bench][tool]['ALL']:
                            print(f'({line[0]},{line[1]})')
                        print('};')
                        print('\\addlegendentry{' + str(tool)+'};')
                        for line in streams[bench][tool]['OOM']:
                            print(f'\draw[orange, thick] (axis cs:{line[0]},{line[1]}) circle (5pt);')
                        for line in streams[bench][tool]['TLE']:
                            print(f'\draw[red, thick] (axis cs:{line[0]},{line[1]}) circle (5pt);')
                        for line in streams[bench][tool]['UNK']:
                            print(f'\draw[brown, thick] (axis cs:{line[0]},{line[1]}) circle (5pt);')
            print("""
                \end{axis}
                \end{tikzpicture}""")





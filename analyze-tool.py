
from csvlib import *
from sys import argv

#print("Analyzing output of benchexec. ")
print("Tool: ", argv[1])
print("CSV files: ", [argv[2]])
#print('Default safety val: ', argv[3])
print("-------------------------------------")

csvs = {}
csvs[argv[1]] = [argv[2]]

tools = {}
stats = {}

for name in csvs:
    tools[name] = Tool(name, csvs[name], argv[3])
    stats[name] = tools[name].stats()

print("Statistics for run ", argv[2:])
print("")
for name in stats:
    stats[name].print()
print("-------------------------------------")

#solved_safe = {}
#solved_unsafe = {}
#for tool in stats:
#    ssafe, sunsafe = stats[tool].solved_benchmarks()
#    solved_safe[tool] = ssafe 
#    solved_unsafe[tool] = sunsafe 
#
#make_diagram(solved_safe, solved_unsafe)


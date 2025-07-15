# High Level System Design

Goal: Given a text file, ouput a 10-word summary.

Nodes:

1. LoadFile (reads a path, loads text -> shared\["raw"\])
2. Summarize (LLM call on shared\["raw"\])
3. PrintResult (just prints)

Flow: LoadFile >> Summarize >> PrintResult

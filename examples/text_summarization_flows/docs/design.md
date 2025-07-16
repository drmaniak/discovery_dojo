# High Level System Design

## [Basic Flow](../basic_flow.py)

Goal: Given a text file, ouput a 10-word summary.

Nodes:

1. LoadFile (reads a path, loads text -> shared\["raw"\])
2. Summarize (LLM call on shared\["raw"\])
3. PrintResult (just prints)

Flow: LoadFile >> Summarize >> PrintResult

## [Branching Flow](../branching_flow.py)

Goal: Given a text file, ouput a 10-word summary.

Nodes:

1. LoadFile (reads a path, loads text -> shared\["raw"\])
2. DecideLength (Reads file contents to determine if "long" or "short")
3. Branch based on length
   a. SummarizeLong (LLM call on shared\["raw"\])
   b. SummarizeShort (LLM call on shared\["raw"\])
4. PrintResult (just prints)

Flow: LoadFile >> DecideLength - "short" >> SummarizeShort >> PrintResult
Flow: LoadFile >> DecideLength - "long" >> SummarizeLong >> PrintResult

## [Batch Flow](../branching_flow.py)

Goal: Given a text file, ouput a 10-word summary.

Nodes:

1. LoadFiles (reads a directory path, loads all .txt files into a shared\["folder"\])
2. FolderBatchFlow (will be run on every filepath in the shared folder)
3. ReadFile (reads a path, loads text -> shared\["raw"\])
4. DecideLength (Reads file contents to determine if "long" or "short")
5. Branch based on length
   a. SummarizeLong (LLM call on shared\["raw"\])
   b. SummarizeShort (LLM call on shared\["raw"\])
6. PrintResult (just prints)

Flow: LoadFile >> FolderBatchFlow(ReadFile >> DecideLength - "short" >> SummarizeShort >> PrintResult)
Flow: LoadFile >> FolderBatchFlow(ReadFile >> DecideLength - "long" >> SummarizeLong >> PrintResult)

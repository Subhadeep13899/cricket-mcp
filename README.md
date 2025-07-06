# cricket-mcp
A fun MCP server for retrieiving details of cricket matches in natural language.

This project exposes two tools that can be called by an LLM:
- A tool to get a list or an overview of cricket matches that have happened in the recent past, are happening or will happen in the near future
- Details of a live, recent or an upcoming cricket match between any two teams

Usage steps:
- Install all requirements (pip install -r requirements.txt)
- Create the LLM MCP config file. A sample has been provided.
- Start (or restart) Claude, or any LLM desktop client of your choice which has MCP support.
- The cricket tools should show up in the tools section.
- Ask the LLM any supported question, such as, "How is India doing against the live match against England?", or "What are some recently concluded cricket matches?"

More APIs might be added soon.

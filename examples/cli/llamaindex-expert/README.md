# LlamaIndex Expert

The [agent_config.yaml](./agent_config.yaml) and the [.mcp.json](./.mcp.json) files available in this folder can be used to create a LlamaIndex expert assistant to build typescript and python applications, thanks to the [Documentation MCP](https://www.llamaindex.ai/blog/adding-native-mcp-to-llamaindex-docs) offered by LlamaIndex.

The agent has also access to memory tools (to store important pieces of information gathered during exploration or deriving from user interaction) and TODO tools (to track its tasks).

Example prompt:

```md
Could you please create an example LlamaIndex Workflow in typescript, using the fan-in/fan-out pattern?
```
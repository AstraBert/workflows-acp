from workflows import Workflow, Context, step
from workflows.resource import ResourceManager

from .llm_wrapper import LLMWrapper
from .events import InputEvent, ThinkingEvent, ObservationEvent, ToolCallEvent, ToolPermissionEvent, ToolResultEvent, AskHumanEvent, HumanAnswerEvent, PermissionResponseEvent, PromptEvent, OutputEvent
from .models import Thought, Observation, Action

class AgentWorkflow(Workflow):
    def __init__(self, llm: LLMWrapper, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.llm = llm
    
    @step
    async def think(self, ev: InputEvent | PromptEvent, ctx: Context) -> ThinkingEvent | OutputEvent:
        if isinstance(ev, InputEvent):
            async with ctx.store.edit_state() as state:
                state.mode = ev.mode
        response = await self.llm.generate(schema=Thought)
        if response is not None:
            event = response.to_event()
            ctx.write_event_to_stream(event)
            return event
        return OutputEvent(error="Could not generate thinking response")

    @step
    async def take_action(self, ev: ThinkingEvent, ctx: Context) -> ToolCallEvent | OutputEvent | AskHumanEvent:
        response = await self.llm.generate(schema=Action)
        if response is not None:
            event = response.to_event()
            if not isinstance(event, OutputEvent):
                ctx.write_event_to_stream(event)
            return event
        return OutputEvent(error="Could not generate action response")

    @step
    async def call_tool(self, ev: ToolCallEvent, ctx: Context) -> ToolPermissionEvent | ToolResultEvent:
        state = await ctx.store.get_state()
        tool = self.llm.get_tool(ev.tool_name)
        if state.mode == "bypass":
            result = await tool.execute(ev.tool_input)
            event = ToolResultEvent(tool_name=ev.tool_name, result = result)
        else:
            event = tool.get_permission(ev.tool_input)
        ctx.write_event_to_stream(event)
        return event
        
    




from workflows import Workflow, Context, step

from .llm_wrapper import LLMWrapper
from .events import InputEvent, ThinkingEvent, ToolCallEvent, ToolPermissionEvent, ToolResultEvent, AskHumanEvent, HumanAnswerEvent, PermissionResponseEvent, PromptEvent, OutputEvent
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
        self.llm.add_user_message(ev.prompt)
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
            if not isinstance(event, (OutputEvent, AskHumanEvent)):
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
            ctx.write_event_to_stream(event)
        else:
            event = tool.get_permission(ev.tool_input)
        return event
    
    @step
    async def tool_permission(self, ev: PermissionResponseEvent, ctx: Context) -> ToolResultEvent | PromptEvent:
        if ev.allow:
            tool = self.llm.get_tool(ev.tool_name)
            result = await tool.execute(ev.tool_input)
            event = ToolResultEvent(tool_name=ev.tool_name, result = result)
        else:
            event = PromptEvent(prompt=f"You are not allowed to call tool {ev.tool_name} with arguments: {ev.tool_input} because of the following reasons: {ev.reason}. Please think of an alternative.")
        ctx.write_event_to_stream(event)
        return event
    
    @step
    async def human_answer(self, ev: HumanAnswerEvent, ctx: Context):
        event = PromptEvent(prompt=f"Here is the answer from the user: {ev.answer}. Please think of the next move.")
        ctx.write_event_to_stream(event)
        return event

    @step
    async def observation(self, ev: ToolResultEvent, ctx: Context):
        self.llm.add_user_message(f"Received the following result: {ev.result} from calling tool: {ev.tool_name}")
        response = await self.llm.generate(schema=Observation)
        if response is not None:
            event = response.to_event()
            ctx.write_event_to_stream(event)
            return event
        return OutputEvent(error="Could not generate observation response")

        


    




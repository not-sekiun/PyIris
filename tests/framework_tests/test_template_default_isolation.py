from consortium.framework.agents import (
    BaseAgentGenerator,
    BaseAgentTemplate,
    BaseAgentType,
)
from consortium.framework.listeners import (
    BaseListener,
    BaseListenerTemplate,
    BaseListenerType,
)
from consortium.framework.options import DictionaryValueOption, ListValueOption


class _DefaultAgentType(BaseAgentType):
    name = "default_isolation_agent"
    agent_capabilities = set()


class _DefaultAgentGenerator(BaseAgentGenerator):
    agent_generator_build_steps = []


class _DefaultAgentTemplate(BaseAgentTemplate):
    label = "consortium.agents.default_isolation"
    agent_generator = _DefaultAgentGenerator
    agent_type = _DefaultAgentType
    compatible_listener_types = set()
    options = {
        ListValueOption("flags", required=False, default_value=["initial"]),
        DictionaryValueOption(
            "settings", required=False, default_value={"mode": "initial"}
        ),
    }


class _DefaultListenerType(BaseListenerType):
    name = "default_isolation_listener"


class _DefaultListener(BaseListener):
    async def on_started(self) -> None: ...

    async def on_running(self) -> None: ...

    async def on_stopped(self) -> None: ...

    async def on_cancelled(self) -> None: ...


class _DefaultListenerTemplate(BaseListenerTemplate):
    label = "consortium.listeners.default_isolation"
    listener = _DefaultListener
    listener_type = _DefaultListenerType
    options = {
        ListValueOption("flags", required=False, default_value=["initial"]),
        DictionaryValueOption(
            "settings", required=False, default_value={"mode": "initial"}
        ),
    }

    def resolve_listener_endpoint(self, parameters) -> str:
        return ""


def test_agent_template_copies_mutable_defaults_per_generator():
    template = _DefaultAgentTemplate()
    first = template.create_agent_generator()
    second = template.create_agent_generator()

    first.parameters["flags"].append("first-only")
    first.parameters["settings"]["mode"] = "first-only"

    assert second.parameters == {"flags": ["initial"], "settings": {"mode": "initial"}}
    assert template.options["flags"].default_value == ["initial"]
    assert template.options["settings"].default_value == {"mode": "initial"}


def test_listener_template_copies_mutable_defaults_per_listener():
    template = _DefaultListenerTemplate()
    first = template.create_listener()
    second = template.create_listener()

    first.parameters["flags"].append("first-only")
    first.parameters["settings"]["mode"] = "first-only"

    assert second.parameters == {"flags": ["initial"], "settings": {"mode": "initial"}}
    assert template.options["flags"].default_value == ["initial"]
    assert template.options["settings"].default_value == {"mode": "initial"}

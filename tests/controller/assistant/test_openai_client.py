"""The OpenAI adapter, against a stand-in SDK: requests, replies, failures, configuration."""

from types import SimpleNamespace

import httpx2
import openai
import pytest

from zimpasta.controller.assistant.client import (
    DEFAULT_MODEL,
    MAX_OUTPUT_TOKENS,
    AIError,
    AINotConfigured,
    OpenAIClient,
    ToolCall,
    client_from_environment,
)

REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/responses")
SECRET = "sk-test-not-a-real-key-1234"


class FakeSDK:
    """The slice of ``openai.OpenAI`` the adapter uses: ``responses.create``."""

    def __init__(self, result) -> None:
        self.result = result
        self.calls: list[dict] = []
        self.responses = SimpleNamespace(create=self.create)

    def create(self, **options):
        self.calls.append(options)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def response(*output, text="", reason=None):
    return SimpleNamespace(
        id="resp_1",
        output=list(output),
        output_text=text,
        incomplete_details=SimpleNamespace(reason=reason) if reason else None,
    )


def function_call(name="validate_configuration", arguments="{}", call_id="call_1"):
    return SimpleNamespace(type="function_call", name=name, arguments=arguments, call_id=call_id)


def ask(client: OpenAIClient, previous_id=None):
    return client.respond(
        instructions="Be helpful.",
        input=[{"role": "user", "content": "Hi"}],
        tools=[{"type": "function", "name": "validate_configuration"}],
        previous_id=previous_id,
    )


def test_a_request_carries_the_model_prompt_tools_and_a_token_bound():
    sdk = FakeSDK(response(text="Hello."))
    client = OpenAIClient(SECRET, "gpt-6-luna", sdk=sdk)

    reply = ask(client)

    [options] = sdk.calls
    assert options["model"] == "gpt-6-luna"
    assert options["instructions"] == "Be helpful."
    assert options["tools"][0]["name"] == "validate_configuration"
    assert options["max_output_tokens"] == MAX_OUTPUT_TOKENS
    assert "previous_response_id" not in options
    assert (reply.id, reply.text, reply.calls) == ("resp_1", "Hello.", ())


def test_tool_calls_are_read_from_the_output_and_continuations_chain():
    sdk = FakeSDK(
        response(
            SimpleNamespace(type="reasoning"),
            function_call(arguments='{"area": "rooms"}', name="inspect_configuration"),
        )
    )

    reply = ask(OpenAIClient(SECRET, sdk=sdk), previous_id="resp_0")

    assert sdk.calls[0]["previous_response_id"] == "resp_0"
    assert reply.calls == (ToolCall("call_1", "inspect_configuration", '{"area": "rooms"}'),)


def test_an_empty_reply_is_a_failure_that_says_why():
    sdk = FakeSDK(response(reason="max_output_tokens"))

    with pytest.raises(AIError, match="stopped without answering \\(max output tokens\\)"):
        ask(OpenAIClient(SECRET, sdk=sdk))


def status_error(cls, status: int):
    return cls("boom", response=httpx2.Response(status, request=REQUEST), body=None)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (status_error(openai.AuthenticationError, 401), "rejected the API key"),
        (status_error(openai.PermissionDeniedError, 403), "rejected the API key"),
        (status_error(openai.RateLimitError, 429), "limiting requests"),
        (status_error(openai.NotFoundError, 404), "doesn't offer the model"),
        (status_error(openai.BadRequestError, 400), "couldn't process the request: boom"),
        (status_error(openai.InternalServerError, 500), "HTTP 500"),
        (openai.APITimeoutError(request=REQUEST), "didn't answer in time"),
        (openai.APIConnectionError(request=REQUEST), "Couldn't reach OpenAI"),
        (RuntimeError("socket closed"), "failed: socket closed"),
    ],
)
def test_api_failures_become_plain_messages(error, expected):
    client = OpenAIClient(SECRET, sdk=FakeSDK(error))

    with pytest.raises(AIError) as caught:
        ask(client)

    assert expected in caught.value.message
    assert SECRET not in caught.value.message
    assert caught.value.code == "ai_unavailable"


def test_the_key_and_model_come_from_the_environment():
    client = client_from_environment({"OPENAI_API_KEY": f"  {SECRET}  "})
    assert client.model == DEFAULT_MODEL == "gpt-6-luna"

    custom = client_from_environment({"OPENAI_API_KEY": SECRET, "ZIMPASTA_AI_MODEL": "gpt-6-astra"})
    assert custom.model == "gpt-6-astra"


@pytest.mark.parametrize("environment", [{}, {"OPENAI_API_KEY": "   "}])
def test_a_missing_key_says_how_to_set_it(environment):
    with pytest.raises(AINotConfigured) as caught:
        client_from_environment(environment)

    assert "OPENAI_API_KEY" in caught.value.message
    assert caught.value.code == "ai_not_configured"

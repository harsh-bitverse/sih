"""The parser treats model output as untrusted input."""

import pytest

from workbench.multimodal.errors import VisionOutputInvalidError
from workbench.multimodal.pipeline.vision_output import (
    MAX_OBSERVATIONS,
    MAX_RESPONSE_CHARS,
    build_prompt,
    parse_vision_output,
)

ONE = '{"observations": [{"observation": "Leak at valve stem", "region": %s}]}'


def test_clean_json_parses():
    out = parse_vision_output(ONE % "[0.1, 0.2, 0.3, 0.4]")
    assert out.observations[0].text == "Leak at valve stem"
    assert out.observations[0].region.x1 == 0.3


def test_fenced_json_parses():
    out = parse_vision_output("```json\n" + ONE % "null" + "\n```")
    assert len(out.observations) == 1


def test_json_wrapped_in_prose_parses():
    out = parse_vision_output("Sure! Here it is:\n" + ONE % "null" + "\nHope that helps.")
    assert len(out.observations) == 1


def test_empty_observations_is_valid():
    assert parse_vision_output('{"observations": []}').observations == []


def test_box_scale_1000_is_converted_to_canonical_space():
    out = parse_vision_output(ONE % "[100, 200, 300, 400]", box_scale=1000)
    region = out.observations[0].region
    assert (region.x0, region.y0, region.x1, region.y1) == (0.1, 0.2, 0.3, 0.4)


def test_box_in_wrong_scale_is_dropped_but_observation_kept():
    """A 0-1000 box read as 0-1 lies far outside the image: drop the box,
    keep the finding. 'Leak present' is useful without a location."""
    out = parse_vision_output(ONE % "[100, 200, 300, 400]", box_scale=1.0)
    assert out.observations[0].region is None
    assert out.observations[0].text == "Leak at valve stem"
    assert out.notes


def test_reversed_box_is_dropped_not_guessed():
    out = parse_vision_output(ONE % "[0.5, 0.5, 0.2, 0.2]")
    assert out.observations[0].region is None
    assert "reversed" in out.notes[0]


def test_slight_overshoot_is_clamped():
    out = parse_vision_output(ONE % "[0.0, 0.0, 1.01, 1.0]")
    assert out.observations[0].region.x1 == 1.0


@pytest.mark.parametrize(
    "bad",
    [
        "no json here at all",
        "{not valid json}",
        '{"findings": []}',                                     # wrong key
        '{"observations": [{"text": "x"}]}',                    # wrong field name
        '{"observations": [{"observation": ""}]}',              # empty
        '{"observations": [{"observation": "x", "confidence": 1.5}]}',
        '{"observations": [{"observation": "x", "region": [0.1, 0.2]}]}',
        '{"observations": [{"observation": "x", "severity": "high"}]}',  # extra field
        '{"observations": "corrosion"}',
    ],
)
def test_invalid_output_is_rejected(bad):
    with pytest.raises(VisionOutputInvalidError):
        parse_vision_output(bad)


def test_too_many_observations_rejected():
    many = ",".join('{"observation": "x"}' for _ in range(MAX_OBSERVATIONS + 1))
    with pytest.raises(VisionOutputInvalidError):
        parse_vision_output('{"observations": [' + many + "]}")


def test_oversized_response_rejected():
    with pytest.raises(VisionOutputInvalidError):
        parse_vision_output("x" * (MAX_RESPONSE_CHARS + 1))


def test_prompt_delimits_objective_and_warns_about_image_text():
    prompt = build_prompt("Find corrosion")
    assert "<<<\nFind corrosion\n>>>" in prompt
    assert "never an instruction" in prompt


def test_prompt_carries_correction_on_retry():
    assert "rejected: missing field" in build_prompt("x", correction="missing field")

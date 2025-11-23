import datetime
import secrets
from collections.abc import Generator

import httpx
import reflex as rx
from reflex.event import EventSpec

from appkit_imagecreator.backend.generator_registry import generator_registry
from appkit_imagecreator.backend.models import (
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)
from appkit_imagecreator.components.styles_preset import styles_preset
from appkit_imagecreator.configuration import prompt_list

DEFAULT_IMAGE = "/img/default.jpg"
API_TOKEN_ENV_VAR = "TOGETHER_API_KEY"  # noqa


general_dimensions: list[tuple[int, int]] = [
    (1536, 1024),
    (1024, 1024),
    (1024, 1536),
]


def copy_script() -> EventSpec:
    return rx.call_script(
        """
        refs['_client_state_setCopying'](true);
        setTimeout(() => {
            refs['_client_state_setCopying'](false);
        }, 1750);
        """
    )


class GeneratorState(rx.State):
    is_generating: bool = False
    _request_id: str = None
    output_image: str = DEFAULT_IMAGE
    output_list: list[str] = []
    is_downloading: bool = False

    @rx.event(background=True)
    async def generate_image(self) -> any:
        try:
            async with self:
                self.is_generating = True
            yield

            async with self:
                options = await self.get_state(OptionsState)
            # If prompt is empty
            if options.prompt == "":
                yield rx.toast.warning("Bitte gib einen Prompt ein.", close_button=True)
                return

            generation_input = GenerationInput(
                prompt=options.prompt + "\n" + options.selected_style_prompt,
                width=options.selected_dimensions[0],
                height=options.selected_dimensions[1],
                negative_prompt=options.negative_prompt,
                steps=options.steps,
                n=options.num_outputs,
                enhance_prompt=options.enhance_prompt,
            )

            if options.seed != 0:
                generation_input.seed = options.seed

            async with self:
                self.is_generating = True

            client: ImageGenerator = generator_registry.get(options.generator)
            response: ImageGeneratorResponse = await client.generate(generation_input)

            if response.state != ImageResponseState.SUCCEEDED or not response:
                async with self:
                    self._reset_state()
                yield rx.toast.error(
                    "Fehler beim generieren: " + response.error, close_button=True
                )
                return

            async with self:
                self.output_image = response.images[0]
                self.output_list = [] if len(response.images) == 1 else response.images
                self._reset_state()

        except Exception as e:
            async with self:
                self._reset_state()
            yield rx.toast.error(f"Bitte versuch es nochmal: {e!s}", close_button=True)
        finally:
            async with self:
                self.is_generating = False

    def cancel_generation(self) -> None:
        self._reset_state()

    def _reset_state(self) -> None:
        self._request_id = None
        self.is_generating = False

    def download_image(self) -> any:
        self.is_downloading = True
        yield
        image_url = self.output_image
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"reflex_ai_{timestamp}.png"

        try:
            if image_url.startswith("http"):
                if "/_upload/" in image_url:
                    file_name = image_url.split("/_upload/")[-1]
                    upload_dir = rx.get_upload_dir()
                    file_path = upload_dir / file_name
                    if file_path.exists():
                        with file_path.open("rb") as f:
                            image_data = f.read()
                        yield rx.download(data=image_data, filename=filename)
                    else:
                        yield rx.toast.error("Datei nicht gefunden", close_button=True)
                else:
                    response = httpx.get(image_url, timeout=30.0)
                    response.raise_for_status()
                    image_data = response.content
                    yield rx.download(data=image_data, filename=filename)
            else:
                yield rx.download(url=image_url, filename=filename)
        except Exception as e:
            yield rx.toast.error(f"Fehler beim Download: {e}", close_button=True)

        self.is_downloading = False
        yield

    def set_output_image(self, image: str) -> None:
        self.output_image = image


class OptionsState(rx.State):
    generator: str = generator_registry.get_default_generator().id
    generators: list[dict[str, str]] = generator_registry.list_generators()
    dimensions: list[tuple[int, int]] = general_dimensions
    slider_tick: int = len(dimensions) // 2
    selected_dimensions: tuple[int, int] = dimensions[slider_tick]
    hover: bool = False
    styles_preset: dict[str, dict[str, str]] = styles_preset
    advanced_options_open: bool = False

    prompt: str = ""
    negative_prompt: str = """unscharfe Details; Kompressionsartefakte; Rauschen; Wasserzeichen; Textüberlagerungen; Signaturen;"""  # noqa: E501
    num_outputs: int = 1
    seed: int = 42
    steps: int = 4
    guidance_scale: float = 0
    selected_style: str = "Photographic"
    enhance_prompt: bool = True

    @rx.event
    def set_tick(self, value: list) -> None:
        self.slider_tick = value[0]
        self.selected_dimensions = self.dimensions[self.slider_tick]

    @rx.event
    def set_hover(self, value: bool) -> None:
        self.hover = value

    @rx.event
    def set_num_outputs(self, value: list) -> None:
        self.num_outputs = value[0]

    @rx.event
    def set_steps(self, value: list) -> Generator:
        self.steps = value[0]
        yield

    @rx.event
    def set_seed(self, value: str) -> None:
        self.seed = int(value)

    @rx.event
    def set_guidance_scale(self, value: list) -> Generator:
        self.guidance_scale = value[0]
        yield

    @rx.event
    def set_generator(self, value: str) -> Generator:
        self.generator = value
        self.dimensions = general_dimensions
        yield

        self.set_tick([len(self.dimensions) // 2])
        self.selected_dimensions: tuple[int, int] = self.dimensions[self.slider_tick]
        yield

    @rx.event
    def set_enhance_prompt(self, value: bool) -> None:
        self.enhance_prompt = value

    @rx.event
    def randomize_prompt(self) -> None:
        self.prompt = secrets.choice(prompt_list)

    @rx.var(cache=False)
    def selected_style_prompt(self) -> str:
        if self.selected_style == "":
            return ""
        return self.styles_preset[self.selected_style]["prompt"]

    @rx.var(cache=False)
    def dimensions_str(self) -> str:
        width, height = self.selected_dimensions
        return f"{width} x {height}"

    @rx.event
    def set_prompt(self, prompt: str) -> None:
        """Explicit setter for prompt (used by UI)."""
        self.prompt = prompt

    @rx.event
    def set_selected_style(self, style: str) -> None:
        """Explicit setter for selected_style (used by UI)."""
        self.selected_style = style

    @rx.event
    def set_negative_prompt(self, prompt: str) -> None:
        """Explicit setter for negative_prompt (used by UI)."""
        self.negative_prompt = prompt

    @rx.event
    def set_advanced_options_open(self, value: bool) -> None:
        """Explicit setter for advanced_options_open (used by UI)."""
        self.advanced_options_open = value

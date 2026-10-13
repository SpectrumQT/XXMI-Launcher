import sys
import logging
import time
import tkinter
import re
import threading
import av

from typing import Union, Tuple, List, Dict, Optional, Callable, Deque, Iterator
from pathlib import Path
from collections import deque
from dataclasses import dataclass

from tkinter import Menu, INSERT, font
from customtkinter import CTkBaseClass, CTkButton, CTkImage, CTkLabel, CTkProgressBar, CTkEntry, CTkCheckBox, CTkTextbox, CTkOptionMenu, CTkRadioButton, StringVar
from customtkinter import END, CURRENT
from customtkinter.windows.widgets.scaling.scaling_base_class import CTkScalingBaseClass
from customtkinter import ThemeManager, CTkFont
from PIL import Image, ImageTk, ImageDraw

import core.config_manager as Config

from gui.classes.element import UIElementBase
from gui.classes.windows import UIWindow

logging.getLogger('PIL').setLevel(logging.INFO)


log = logging.getLogger(__name__)


class UIWidget(UIElementBase):
    def __init__(self, master, **kwargs):
        UIElementBase.__init__(self, **kwargs)
        self.master = master
        # CTkBaseClass.__init__(self, master=master)


class UICanvasWidget(UIWidget):
    def winfo_rootx(self):
        x = self.winfo_x()
        if self._anchor in ['center', 'n', 's']:
            return self.canvas.winfo_rootx() + x - int(self.winfo_width() / 2)
        return self.canvas.winfo_rootx() + x

    def winfo_rooty(self):
        y = self.winfo_y()
        if self._anchor in ['center', 'w', 'e']:
            return self.canvas.winfo_rooty() + y - int(self.winfo_height() / 2)
        return self.canvas.winfo_rooty() + y

    def winfo_width(self):
        return self._width

    def winfo_height(self):
        return self._height

    def winfo_x(self):
        return self._x

    def winfo_y(self):
        return self._y


class UIText(UICanvasWidget, CTkBaseClass):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 font: str,
                 fill: str = 'black',
                 activefill: str = 'black',
                 disabledfill: str = 'black',
                 justify: str = 'left',
                 state: str = '',
                 tags: str = '',
                 width: int = 0,
                 text: str = '',
                 x: int = 0,
                 y: int = 0,
                 canvas=None,
                 anchor=None,
                 max_width=0,
                 **kwargs):
        if 'Asap' in font:
            y -= 1
        self.master = master
        self.canvas = canvas or master.canvas
        CTkBaseClass.__init__(self, master=master)
        UIWidget.__init__(self, master, **kwargs)
        self.fill = fill
        self.activefill = activefill
        self.disabledfill = disabledfill
        self._x = None
        self._y = None
        self._width = None
        self._height = None
        self._font_obj = None
        self._anchor = anchor
        self._max_width = max_width

        if isinstance(font, str):
            font_pattern = re.compile(r'(?P<family>.*)\s(?P<size>\d+)\s*(?P<weight>.*)?')
            result = list(re.finditer(font_pattern, font))
            if len(result) != 1:
                raise ValueError(f'Failed to parse font from {font}!')
            font = result[0].groupdict()
            if font['weight']:
                font = (font['family'], int(font['size']), font['weight'])
            else:
                font = (font['family'], int(font['size']))

        self._font = CTkFont() if font is None else self._check_font_type(font)

        self._text_id = self.canvas.create_text(0, 0)

        self.configure(fill=fill, activefill=activefill, disabledfill=disabledfill, justify=justify, state=state,
                       tags=tags, width=width, font=self._font, text=text, anchor=anchor, **kwargs)
        self.set(text)

        self._apply_theme()

        self.move(x, y)

    def configure(self, require_redraw=False, **kwargs):
        if "font" in kwargs:
            self._font = self._apply_font_scaling(tuple(kwargs.pop("font")))
            self._font_obj = font.Font(family=self._font[0], size=self._font[1])
            self._height = int(self._font_obj.metrics('linespace') / self._apply_widget_scaling(1))
            self.canvas.itemconfig(self._text_id, font=self._font)

        self.canvas.itemconfig(self._text_id, **kwargs)

    def move(self, x, y):
        self._x = int(self._apply_widget_scaling(x))
        self._y = int(self._apply_widget_scaling(y))
        self.canvas.coords(self._text_id, self._x, self._y)

    def set(self, text: str):
        text = self._truncate_text(text)
        self.canvas.itemconfigure(self._text_id, text=text)
        self._width = self._measure_text(text)

    def _show(self):
        self.canvas.itemconfigure(self._text_id, state='normal')

    def _hide(self):
        self.canvas.itemconfigure(self._text_id, state='hidden')

    def force_normal(self):
        self.canvas.itemconfigure(self._text_id, fill=self.fill)

    def force_active(self):
        self.canvas.itemconfigure(self._text_id, fill=self.activefill, activefill=self.activefill)

    def force_disabled(self):
        self.canvas.itemconfigure(self._text_id, fill=self.disabledfill, activefill=self.disabledfill)

    def bind(self, *args, **kwargs):
        self.canvas.tag_bind(self._text_id, *args, **kwargs)

    def unbind(self, *args, **kwargs):
        self.canvas.tag_unbind(self._text_id, *args, **kwargs)

    def destroy(self):
        try:
            self.canvas.delete(self._text_id)
        except:
            pass
        super().destroy()

    def _measure_text(self, text: str) -> int:
        return int(self._font_obj.measure(text) / self._apply_widget_scaling(1))

    def _truncate_text(self, text: str, ellipsis: str = "...") -> str:
        if self._max_width <= 0:
            return text

        if self._measure_text(text) <= self._max_width:
            return text

        while text and self._measure_text(text + ellipsis) > self._max_width:
            text = text[:-1]

        return text + ellipsis if text else ellipsis


AnimationFrame = tuple[int, Image.Image, int]
class _PyAVVideoSource:
    """Description of a media file decoded by PyAV.

    `output_size` is the requested `(width, height)` of decoded frames and
    should be set by the host widget before playback starts.
    """

    def __init__(
        self,
        path: str | Path,
        output_size: tuple[int, int] = (0, 0),
    ) -> None:
        self.path = str(path)
        self.output_size = output_size
        self.n_frames = 2  # Updated from stream metadata when available.
        self.fps = 30.0
        self.frame_duration_ms = 33


class AnimationMixin:
    """Background-decoded, looping animation playback for Tk widgets.

    Implement `_get_animation_source` and `_display_animation_frame` in the host widget.
    The source hook must return a `_PyAVVideoSource` or `None`.
    Frames are scaled and converted to RGBA by the PyAV filter graph;
    Pillow is used only to hand those frames to the existing rendering hook.
    """

    _ANIMATION_RETRY_MS = 4
    _ANIMATION_MIN_DELAY_MS = 2

    # Reserve time for Tk to process tooltips, redraws, and input events.
    _ANIMATION_MIN_IDLE_MS = 8
    _ANIMATION_RENDER_UTILIZATION = 0.5

    def _init_animation(self) -> None:
        self._anim_condition = threading.Condition()
        self._anim_buffer: Deque[AnimationFrame] = deque(maxlen=1)

        self._anim_enable_alpha = False
        self._anim_fps_limit = 60.0  # Maximum presentation FPS (not source FPS).

        self._anim_worker: threading.Thread | None = None
        self._anim_worker_stop = threading.Event()
        self._anim_generation = 0
        self._anim_job = None
        self._anim_render_ms = 0.0

        self._anim_is_running = False
        self._anim_is_paused = False
        self._anim_pause_reasons: set[str] = set()
        self._anim_paused_at = 0.0
        self._anim_total_paused_seconds = 0.0
        self._anim_displayed_index: int | None = None

        self._anim_displayed_count = 0
        self._anim_dropped_count = 0
        self._anim_last_displayed_index = None

        self._anim_throughput_started = time.perf_counter()
        self._anim_throughput_displayed = 0
        self._anim_effective_fps = 0.0
    def _scale_delay(self, delay: int) -> int:
        # Rendering cost is largely driven by the number of pixels submitted to the canvas.
        # When both dimensions scale by factor s, pixel count grows approximately as s²:
        #
        #   Scaling 1.0  1280x720   (1.0x pixels)
        #   Scaling 1.5	 1920x1080  (2.25x pixels)
        #   Scaling 2.0	 2560x1440  (4.0x pixels)
        #
        # Baseline delays are empirically tuned for ~60 FPS at 720p.
        # Here we increase delays proportionally to pixel count to throttle rendering
        # as resolution grows to help preserve nearly the same GUI responsiveness.
        scaling_factor = self._apply_widget_scaling(1.0)
        return int(delay * (scaling_factor ** 2))

    
    # region Host-widget Hooks

    def _get_animation_source(self) -> _PyAVVideoSource | None:
        raise NotImplementedError

    def _display_animation_frame(self, frame_data: AnimationFrame) -> None:
        """Display a prepared frame on the Tk thread."""
        raise NotImplementedError

    def _has_animation(self) -> bool:
        return self._get_animation_source() is not None

    def _worker_is_obsolete(
        self,
        generation: int,
        stop_event: threading.Event,
    ) -> bool:
        return stop_event.is_set() or generation != self._anim_generation

    # endregion

    # region Animation Lifecycle

    def start_animation(self) -> None:
        source = self._get_animation_source()
        if source is None:
            return

        if not isinstance(source, _PyAVVideoSource):
            return

        if self._anim_pause_reasons:
            self._anim_is_paused = True
            return
        if self._anim_is_running:
            return

        with self._anim_condition:
            self._anim_is_running = True
            self._anim_is_paused = False
            self._anim_paused_at = 0.0
            self._anim_total_paused_seconds = 0.0
            self._anim_displayed_index = None
            self._anim_buffer.clear()

            # Start fresh moving averages for each playback session.
            self._anim_render_fps = 0.0
            self._anim_filter_fps = 0.0
            self._anim_source_fps = 0.0
            self._anim_throughput_started = time.perf_counter()
            self._anim_throughput_displayed = 0
            self._anim_effective_fps = 0.0
            self._anim_condition.notify_all()

        self._animation_tick()
        self._ensure_animation_worker()
        self._schedule_animation_callback(self._scale_delay(self._ANIMATION_MIN_DELAY_MS))

    def stop_animation(self) -> None:
        self._anim_generation += 1
        self._cancel_animation_callback()

        with self._anim_condition:
            self._anim_is_running = False
            self._anim_worker_stop.set()
            self._anim_buffer.clear()
            self._anim_paused_at = 0.0
            self._anim_displayed_index = None
            self._anim_condition.notify_all()

    def pause_animation(self, reason: str = "default") -> None:
        if not self._has_animation():
            return

        self._anim_pause_reasons.add(reason)
        if self._anim_is_paused:
            return

        with self._anim_condition:
            self._anim_is_paused = True
            self._anim_paused_at = time.perf_counter()
            self._anim_condition.notify_all()
        self._cancel_animation_callback()

    def resume_animation(self, reason: str = "default") -> None:
        self._anim_pause_reasons.discard(reason)
        if self._anim_pause_reasons or not self._anim_is_paused:
            return

        with self._anim_condition:
            if self._anim_paused_at:
                self._anim_total_paused_seconds += max(0.0, time.perf_counter() - self._anim_paused_at)
            self._anim_paused_at = 0.0
            self._anim_is_paused = False
            self._anim_condition.notify_all()

        if not self._anim_is_running:
            self.start_animation()
            return

        self._ensure_animation_worker()
        self._schedule_animation_callback(self._scale_delay(self._ANIMATION_MIN_DELAY_MS))

    # endregion

    # region Tk Callback Scheduling

    def _schedule_animation_callback(self, delay_ms: int) -> None:
        if not self._anim_is_running or self._anim_is_paused or self._anim_job is not None:
            return

        idle_ms = self._get_animation_idle_delay_ms()

        try:
            self._anim_job = self.after(idle_ms + int(delay_ms), self._animation_tick)
        except Exception:
            log.debug("Unable to schedule animation callback", exc_info=True)
            self.stop_animation()

    def _cancel_animation_callback(self) -> None:
        job = self._anim_job
        self._anim_job = None
        if job is None:
            return
        try:
            self.after_cancel(job)
        except Exception:
            # after_cancel can fail if the widget or Tcl interpreter is gone.
            log.debug("Animation callback was unavailable", exc_info=True)

    def _animation_tick(self) -> None:
        self._anim_job = None
        if not self._anim_is_running or self._anim_is_paused:
            return

        source = self._get_animation_source()
        if source is None or not isinstance(source, _PyAVVideoSource):
            if source is not None:
                log.error("Animation source changed to an unsupported type during playback")
            self.stop_animation()
            return

        try:
            canvas = getattr(self, "canvas", None)
            if canvas is not None and not canvas.winfo_exists():
                self.stop_animation()
                return
        except Exception:
            self.stop_animation()
            return

        with self._anim_condition:
            frame_data = self._anim_buffer.pop() if self._anim_buffer else None
            self._anim_condition.notify_all()

        if frame_data is not None:
            try:
                render_started = time.perf_counter()
                self._display_animation_frame(frame_data)
                render_ms = (time.perf_counter() - render_started) * 1000.0

                self._anim_throughput_displayed += 1

                now = time.perf_counter()
                elapsed = now - self._anim_throughput_started

                if elapsed >= 1.0:
                    self._anim_effective_fps = self._anim_throughput_displayed / elapsed
                    self._anim_throughput_displayed = 0
                    self._anim_throughput_started = now

                if self._anim_render_ms <= 0.0:
                    self._anim_render_ms = render_ms
                else:
                    # Exponential smoothing avoids overreacting to one slow frame.
                    self._anim_render_ms = self._anim_render_ms * 0.7 + render_ms * 0.3
                self._anim_displayed_index = frame_data[0]
            except Exception:
                log.exception("Failed to render animation frame")
                self.stop_animation()
                return

        # The worker paces frames. Poll quickly just after a render, otherwise
        # wake near the next expected frame to avoid excessive Tk event traffic.
        delay = (
            self._scale_delay(self._ANIMATION_MIN_DELAY_MS)
            if frame_data is not None
            else max(self._scale_delay(self._ANIMATION_RETRY_MS), source.frame_duration_ms)
        )
        self._schedule_animation_callback(delay)

    def _get_animation_idle_delay_ms(self) -> int:
        """Return the idle interval while preserving the scaling strategy."""
        render_ms = max(0.0, self._anim_render_ms)

        render_idle_ms = (
            round(render_ms * (1.0 / self._ANIMATION_RENDER_UTILIZATION - 1.0))
            if render_ms > 0.0
            else 0
        )

        return max(self._scale_delay(self._ANIMATION_MIN_IDLE_MS), render_idle_ms)

    def _get_animation_effective_fps_limit(self) -> float:
        """Estimate the sustainable animation FPS at the current render cost.

        The estimate includes rendering time, the configured Tk idle interval,
        and the minimum delay before scheduling the next render callback.
        """
        render_ms = max(0.0, self._anim_render_ms)
        idle_ms = self._get_animation_idle_delay_ms()

        callback_period_ms = render_ms + idle_ms + self._scale_delay(self._ANIMATION_MIN_DELAY_MS)

        return 1000.0 / max(1.0, callback_period_ms)

    # endregion

    # region Background Worker Lifecycle

    def _ensure_animation_worker(self) -> None:
        if not self._anim_is_running or self._anim_is_paused:
            return

        with self._anim_condition:
            if self._anim_worker is not None and self._anim_worker.is_alive():
                self._anim_condition.notify_all()
                return

            self._anim_worker_stop = threading.Event()
            stop_event = self._anim_worker_stop
            generation = self._anim_generation
            worker = threading.Thread(
                target=self._animation_worker,
                args=(generation, stop_event),
                name=f"PyAVAnimation-{id(self):x}",
                daemon=True,
            )
            self._anim_worker = worker
            worker.start()

    def _animation_worker(
        self,
        generation: int,
        stop_event: threading.Event,
    ) -> None:
        try:
            if self._worker_is_obsolete(generation, stop_event):
                return

            source = self._get_animation_source()
            if source is None:
                raise RuntimeError("Animation source disappeared during playback")
            if not isinstance(source, _PyAVVideoSource):
                raise TypeError(
                    "Animation source must be a _PyAVVideoSource; "
                    "Pillow-decoded animations are no longer supported."
                )
            self._video_worker(generation, stop_event, source)
        except Exception:
            log.exception("Animation decoder failed")
            with self._anim_condition:
                if generation == self._anim_generation:
                    self._anim_is_running = False
                    self._anim_worker_stop.set()
                    self._anim_buffer.clear()
                self._anim_condition.notify_all()
        finally:
            with self._anim_condition:
                if self._anim_worker is threading.current_thread():
                    self._anim_worker = None

                # If a new session started before this worker exited, its decoder
                # is launched here once the previous worker has fully terminated.
                restart = (
                    self._anim_is_running
                    and not self._anim_is_paused
                    and generation != self._anim_generation
                )
                self._anim_condition.notify_all()

            if restart:
                self._ensure_animation_worker()

    # endregion

    # region PyAV Video Decoding

    @staticmethod
    def _get_video_stream(container: av.container.InputContainer, source: _PyAVVideoSource):
        streams = container.streams.video
        if not streams:
            return None

        # Some AVIF files expose a thumbnail before the primary image stream.
        stream_index = 1 if source.path.lower().endswith(".avif") and len(streams) > 1 else 0
        return streams[stream_index]

    def _get_video_fps(self, video_stream: av.video.stream.VideoStream) -> float:
        rate = video_stream.average_rate or video_stream.guessed_rate or video_stream.base_rate or 30.0
        return max(1.0, float(rate))

    @staticmethod
    def _validate_output_size(output_size: tuple[int, int]) -> tuple[int, int]:
        if len(output_size) != 2:
            raise ValueError("output_size must contain (width, height)")
        width, height = output_size
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            raise ValueError(f"Invalid animation output size: {output_size!r}")
        return width, height

    def _create_video_filter_graph(
        self,
        video_stream: av.video.stream.VideoStream,
        output_size: tuple[int, int],
        *,
        fps: float | None = None,
    ) -> av.filter.Graph:
        """Build a PyAV graph that scales frames and converts them to RGBA."""
        width, height = self._validate_output_size(output_size)
        graph = av.filter.Graph()
        previous = graph.add_buffer(template=video_stream)

        if fps is not None:
            fps_filter = graph.add("fps", args=f"fps={fps:.6g}")
            previous.link_to(fps_filter)
            previous = fps_filter

        scale_filter = graph.add("scale", args=f"{width}:{height}:flags=lanczos")
        previous.link_to(scale_filter)

        format_filter = graph.add("format", args=f"pix_fmts={'rgba' if self._anim_enable_alpha else 'rgb24'}")
        scale_filter.link_to(format_filter)

        sink = graph.add("buffersink")
        format_filter.link_to(sink)
        graph.configure()
        return graph

    def _decode_first_video_frame(self, source: _PyAVVideoSource) -> Image.Image:
        """Decode the first frame synchronously for initial widget presentation."""
        with av.open(source.path) as container:
            video_stream = self._get_video_stream(container, source)
            if video_stream is None:
                raise ValueError(f"No video stream found: {source.path}")

            graph = self._create_video_filter_graph(video_stream, source.output_size)
            for decoded_frame in container.decode(video_stream):
                graph.push(decoded_frame)
                try:
                    return graph.pull().to_image().convert("RGBA" if self._anim_enable_alpha else "RGB")
                except av.error.BlockingIOError:
                    continue

            # Flush filters in case the first frame was buffered by the graph.
            graph.push(None)
            try:
                return graph.pull().to_image().convert("RGBA" if self._anim_enable_alpha else "RGB")
            except (av.error.BlockingIOError, av.error.EOFError):
                raise ValueError(f"No decodable video frames: {source.path}") from None


            from itertools import chain

    @staticmethod
    def _iter_filtered_frames(
        container: av.container.InputContainer,
        video_stream: av.video.stream.VideoStream,
        graph: av.filter.Graph,
    ) -> Iterator[av.VideoFrame]:
        """Yield all available graph output, including delayed frames at EOF."""
        for decoded_frame in container.decode(video_stream):
            graph.push(decoded_frame)
            while True:
                try:
                    yield graph.pull()
                except av.error.BlockingIOError:
                    break

        graph.push(None)
        while True:
            try:
                yield graph.pull()
            except (av.error.BlockingIOError, av.error.EOFError):
                break

    def _wait_and_buffer_video_frame(
        self,
        generation: int,
        stop_event: threading.Event,
        source: _PyAVVideoSource,
        frame_index: int,
        fps: float,
        playback_started: float,
        paused_total_seen: float,
        prepared_frame: Image.Image,
    ) -> tuple[float, float] | None:
        """Pace a prepared frame, respecting pause/resume, then queue it.

        When the source FPS is within Tkinter's estimated rendering capacity,
        wait for a buffer slot rather than dropping a pending frame.

        When the source FPS exceeds that capacity, keep only the newest pending
        frame to avoid building up playback latency.

        Returns the adjusted playback origin, or None when this playback
        generation has been stopped or superseded.
        """
        frame_data: AnimationFrame = (
            frame_index,
            prepared_frame,
            source.frame_duration_ms,
        )
        media_time = frame_index / fps

        with self._anim_condition:
            while True:
                if self._worker_is_obsolete(generation, stop_event):
                    return None

                # Account for pauses even if decoding completes after a very
                # short pause has already been resumed.
                total_paused = self._anim_total_paused_seconds
                if total_paused > paused_total_seen:
                    playback_started += total_paused - paused_total_seen
                    paused_total_seen = total_paused

                if not self._anim_is_running or self._anim_is_paused:
                    self._anim_condition.wait()
                    continue

                deadline = playback_started + media_time
                remaining = deadline - time.perf_counter()

                if remaining > 0:
                    self._anim_condition.wait(timeout=remaining)
                    continue

                # Estimate Tkinter's current sustainable presentation rate.
                effective_fps_limit = (
                    self._get_animation_effective_fps_limit()
                )

                if fps <= effective_fps_limit:
                    # Tkinter should be able to keep up. Never overwrite a
                    # pending frame; wait until the UI consumes it.
                    if self._anim_buffer:
                        self._anim_condition.wait()
                        continue
                else:
                    # Rendering cannot reliably keep up with the video.
                    # Drop stale pending frames to minimize playback latency.
                    if self._anim_buffer:
                        skipped_index = self._anim_buffer[-1][0]
                        self._anim_dropped_count += 1

                        # print(
                        #     f"[Animation] Dropped pending frame {skipped_index}; "
                        #     f"source={fps:.1f} FPS, "
                        #     f"measured Tk throughput={self._anim_effective_fps:.1f} FPS, "
                        #     f"total dropped={self._anim_dropped_count}"
                        # )

                    self._anim_buffer.clear()

                self._anim_buffer.append(frame_data)
                self._anim_condition.notify_all()
                return playback_started, paused_total_seen

    def _video_worker(
        self,
        generation: int,
        stop_event: threading.Event,
        source: _PyAVVideoSource,
    ) -> None:
        self._validate_output_size(source.output_size)

        while not self._worker_is_obsolete(generation, stop_event):
            emitted_frames = 0
            with av.open(source.path) as container:
                video_stream = self._get_video_stream(container, source)
                if video_stream is None:
                    raise ValueError(f"No video stream found: {source.path}")

                # print(
                #     f"[Animation] Stream FPS: "
                #     f"average={video_stream.average_rate}, "
                #     f"guessed={video_stream.guessed_rate}, "
                #     f"base={video_stream.base_rate}, "
                #     f"selected={self._get_video_fps(video_stream):.2f}"
                # )

                source_fps = self._get_video_fps(video_stream)
                fps = min(source_fps, self._anim_fps_limit)

                source.fps = fps
                source.frame_duration_ms = max(1, round(1000.0 / fps))

                with self._anim_condition:
                    self._anim_source_fps = self._update_fps_average(self._anim_source_fps, source_fps)

                duration_seconds = 0.0
                if video_stream.duration is not None and video_stream.time_base is not None:
                    duration_seconds = float(video_stream.duration * video_stream.time_base)
                elif container.duration is not None:
                    duration_seconds = float(container.duration / av.time_base)
                if duration_seconds > 0:
                    source.n_frames = max(2, round(duration_seconds * fps))

                graph = self._create_video_filter_graph(video_stream, source.output_size, fps=fps)

                # Establish the playback clock only while playback is active;
                # pauses during container setup must not shift the timeline.
                with self._anim_condition:
                    while (
                        not self._worker_is_obsolete(generation, stop_event)
                        and (not self._anim_is_running or self._anim_is_paused)
                    ):
                        self._anim_condition.wait()
                    if self._worker_is_obsolete(generation, stop_event):
                        return
                    playback_started = time.perf_counter()
                    paused_total_seen = self._anim_total_paused_seconds

                filtered_count = 0
                filtered_started = time.perf_counter()

                for frame_index, av_frame in enumerate(self._iter_filtered_frames(container, video_stream, graph)):
                    filtered_count += 1

                    if self._worker_is_obsolete(generation, stop_event):
                        return

                    # PyAV already scaled the frame and converted it to RGB(A).
                    prepared = av_frame.to_image().convert("RGBA" if self._anim_enable_alpha else "RGB")
                    pacing_state = self._wait_and_buffer_video_frame(
                        generation,
                        stop_event,
                        source,
                        frame_index,
                        fps,
                        playback_started,
                        paused_total_seen,
                        prepared,
                    )
                    if pacing_state is None:
                        return
                    playback_started, paused_total_seen = pacing_state
                    emitted_frames += 1

            if emitted_frames == 0:
                raise ValueError(f"No decodable video frames: {source.path}")

    # endregion


class UIImage(AnimationMixin, UICanvasWidget, CTkBaseClass):
    def __init__(
        self,
        master: Union[UIWindow, 'UIFrame'],
        canvas=None,
        image_path: Optional[Union[Path, Image]] = None,
        x: int = 0,
        y: int = 0,
        width: int = 64,
        height: int = 64,
        anchor: str = 'center',
        opacity: float = 1,
        brightness: float = 1,
        fg_color: Optional[Union[str, Tuple[str, str]]] = None,
        border_radius: int = 0,
        border_width: int = 0,
        border_color: Optional[Union[str, Tuple[str, str]]] = None,
        bg_opacity = 0,
        padx = None,
        pady = None,
        anim_start_delay: int = 0,
        **kwargs
    ):
        self.master = master
        self.canvas = canvas or master.canvas
        CTkBaseClass.__init__(self, master=master)
        UIWidget.__init__(self, master, **kwargs)

        self._x = None
        self._y = None
        self._width = None
        self._height = None
        self._anchor = None
        self.opacity = None
        self.brightness = None

        self._image = None
        self.image = None
        self.image_path = None
        self.image_tag = None

        # self._supported_extensions = ['.mp4', '.mkv', '.avi', '.gif', '.webp', '.jpeg', '.png', '.jpg']
        self._supported_extensions = ['.webp', '.jpeg', '.png', '.jpg', '.gif', '.avif', '.mp4', '.webm']

        self._init_animation()
        self._anim_start_delay = anim_start_delay

        self.fg_color = None
        self.border_radius = None
        self.border_width = None
        self.border_color = None
        self.bg_opacity = None
        self.padx = None
        self.pady = None
        self.secondary_fill_color = None
        self.split = None
        self.split_direction = None

        self.configure(image_path=image_path, x=x, y=y, width=width, height=height, anchor=anchor,
                       opacity=opacity, brightness=brightness, fg_color=fg_color, border_radius=border_radius,
                       border_width=border_width, border_color=border_color, bg_opacity=bg_opacity, padx=padx, pady=pady, **kwargs)

        self._apply_theme()

    def configure(self, **kwargs):
        if self._update_attrs(['fg_color', 'border_radius', 'border_width', 'border_color', 'bg_opacity', 'padx', 'pady', 'secondary_fill_color', 'split', 'split_direction'], kwargs) or any(x in kwargs for x in ['width', 'height', 'image_path']):
            if self.fg_color or self.border_radius:
                image_path = kwargs.get('image_path', self.image_path)
                width = kwargs.get('width', self._width)
                height = kwargs.get('height', self._height)
                new_image = self.create_rectangle(
                    width=width,
                    height=height,
                    fill_color=self.fg_color,
                    radius=self.border_radius,
                    border_width=self.border_width,
                    border_color=self.border_color,
                    bg_opacity=self.bg_opacity,
                    padx=self.padx,
                    pady=self.pady,
                    # scale=4,
                    secondary_fill_color=self.secondary_fill_color,
                    split=self.split,
                    split_direction=self.split_direction,
                )
                width, height = new_image.width, new_image.height
                if image_path is not None:
                    image_path = self.compose_image_centered(image_path, new_image)
                else:
                    image_path = new_image
                kwargs['image_path'] = image_path
                kwargs['width'] = width
                kwargs['height'] = height

        if self._update_attrs(['image_path'], kwargs):
            self.stop_animation()

            if isinstance(self.image_path, Image.Image):
                self._image = self.image_path
                self.image_path = None
            else:
                path = Path(self.image_path)

                # Resolve relative path from active theme
                # Also search for files with same name but different extension to support advanced themes
                if not path.is_absolute():
                    path = Config.get_resource_path(self, path, self._supported_extensions)

                is_animated = path.suffix.lower() in { ".webm", ".mp4" }

                image = None
                if not is_animated:
                    image = Image.open(str(path))
                    is_animated = getattr(image, "is_animated", False) and getattr(image, "n_frames", 1) > 1

                if is_animated:
                    self._image = _PyAVVideoSource(path)
                else:
                    self._image = image

        if self._update_attrs(['width', 'height', 'opacity', 'brightness'], kwargs):
            # In configure()
            is_video = isinstance(self._image, _PyAVVideoSource)

            if is_video:
                self._image.output_size = (
                    max(1, int(self._apply_widget_scaling(self._width))),
                    max(1, int(self._apply_widget_scaling(self._height))),
                )
                # Resolve and display the first frame immediately.
                try:
                    first_frame = self._decode_first_video_frame(self._image)
                    self.image = ImageTk.PhotoImage(self._prepare_image(first_frame))
                except Exception:
                    log.exception("Unable to decode the initial video frame")
                    self.image = None
            else:
                self.image = ImageTk.PhotoImage(self._prepare_image(self._image))

            if self.image_tag is None:
                self._update_attrs(['x', 'y', 'anchor'], kwargs)
                self.image_tag = self.canvas.create_image(
                    self._x, self._y, anchor=self._anchor, **kwargs
                )

            if self.image is not None:
                self.set_image(self.image)

            if is_video and self._anim_start_delay >= 0:
                self.after(self._anim_start_delay, self.start_animation)

        if self._update_attrs(['x', 'y'], kwargs):
            self.move(self._x, self._y)

        if self._update_attrs(['anchor'], kwargs):
            self.canvas.itemconfigure(self.image_tag, anchor=self._anchor)

    def _update_attrs(self, attrs, kwargs):
        attrs_updated = False
        for arg in attrs:
            if arg in kwargs:
                value = kwargs.pop(arg)
                if arg in ['x', 'y']:
                    arg = '_' + arg
                    value = int(self._apply_widget_scaling(value))
                if arg in ['width', 'height', 'anchor']:
                    arg = '_' + arg
                setattr(self, arg, value)
                attrs_updated = True
        return attrs_updated

    def set_image(self, image):
        self.canvas.itemconfig(self.image_tag, image=image)

    @staticmethod
    def get_pad_value(x) -> int:
        if x is None:
            return 0
        if isinstance(x, tuple):
            return x[0]
        if isinstance(x, list):
            return x[0]
        return int(x)

    @staticmethod
    def get_pad_sum(x) -> int:
        if x is None:
            return 0
        if isinstance(x, int):
            return x
        if isinstance(x, float):
            return int(x)
        return sum(x)

    def create_rectangle(
        self,
        width,
        height,
        fill_color,
        radius,
        border_width,
        border_color,
        bg_opacity=0,
        padx=None,
        pady=None,
        scale=4,
        secondary_fill_color=None,
        split=0.5,
        split_direction="vertical",
    ):
        bg_image = None
        if padx or pady:
            padded_width = width + self.get_pad_sum(padx) * 2
            padded_height = height + self.get_pad_sum(pady) * 2
            bg_opacity = max(0.0, min(1.0, bg_opacity))
            bg_image = Image.new("RGBA", (padded_width, padded_height),(0, 0, 0, int(bg_opacity * 255)))

        image = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
        border_width *= scale

        draw = ImageDraw.Draw(image)
        box = [
            (border_width // 2, border_width // 2),
            (width * scale - border_width // 2 - 1,
             height * scale - border_width // 2 - 1)
        ]

        if secondary_fill_color is None:
            fill_color_2 = fill_color
        else:
            fill_color_2 = secondary_fill_color

        draw.rounded_rectangle(box, radius=radius * scale, fill=fill_color_2)

        if split and secondary_fill_color is not None:
            split = max(0.0, min(1.0, split))
            if split_direction == "vertical":
                split_pos = int(width * scale * split)
                draw.rectangle((0, 0, split_pos, height * scale), fill=fill_color)
            elif split_direction == "horizontal":
                split_pos = int(height * scale * split)
                draw.rectangle((0, 0, width * scale, split_pos), fill=fill_color)
            else:
                raise ValueError("split_direction must be 'vertical' or 'horizontal'")

            # Restore rounded corners after the rectangular split.
            mask = Image.new("L", image.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius * scale, fill=255)
            image.putalpha(mask)

        if border_width:
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle(box, radius=radius * scale, outline=border_color, width=border_width)

        if scale != 1:
            image = image.resize((width, height), Image.LANCZOS)

        if bg_image:
            bg_image.alpha_composite(image, (self.get_pad_value(padx), self.get_pad_value(pady)))
            return bg_image

        return image

    @staticmethod
    def compose_image_centered(bg, fg):
        bg = bg.copy()
        x = (bg.width - fg.width) // 2
        y = (bg.height - fg.height) // 2
        bg.alpha_composite(fg, (x, y))
        return bg

    def _prepare_image(self, image: Image.Image) -> Image.Image:
        """Modify image size, opacity and/or brightness."""
        image = image.convert("RGBA")

        if self.opacity != 1 or self.brightness != 1:
            red, green, blue, alpha = image.split()

            if self.brightness != 1:
                def adjust_brightness(value):
                    return max(0, min(255, int(value * self.brightness)))

                red = red.point(adjust_brightness)
                green = green.point(adjust_brightness)
                blue = blue.point(adjust_brightness)

            if self.opacity != 1:
                def adjust_opacity(value):
                    return max(0, min(255, int(value * self.opacity)))

                alpha = alpha.point(adjust_opacity)

            image = Image.merge("RGBA", (red, green, blue, alpha))

        width = max(1, int(self._apply_widget_scaling(self._width)))
        height = max(1, int(self._apply_widget_scaling(self._height)))

        if image.size != (width, height):
            image = image.resize((width, height), Image.Resampling.LANCZOS)

        return image

    def _get_animation_source(self) -> Image.Image | None:
        """Expose the Pillow source used by the animation engine."""
        return self._image

    def _prepare_animation_frame(self, frame: Image.Image) -> Image.Image:
        """Apply this widget's visual settings to a decoded animation frame."""
        return self._prepare_image(frame)

    def _display_animation_frame(self, frame_data: tuple) -> None:
        """Display a prepared frame using two reusable Tk images."""
        index, prepared, _duration = frame_data

        if self.image is None or self.image.width() != prepared.width or self.image.height() != prepared.height:
            # Allocate the two buffers only once (or if frame dimensions change).
            self.image = ImageTk.PhotoImage(prepared)
            self.set_image(self.image)
        else:
            # Update the image that is NOT currently displayed.
            self.image.paste(prepared)

        self._anim_index = (index + 1) % self._image.n_frames

        with self._anim_condition:
            self._anim_displayed_index = index
            self._anim_condition.notify_all()

    def move(self, x, y):
        self._x = int(self._apply_widget_scaling(x))
        self._y = int(self._apply_widget_scaling(y))
        self.canvas.coords(self.image_tag, self._x, self._y)

    def _show(self):
        self.canvas.itemconfigure(self.image_tag, state='normal')
        self.resume_animation()

    def _hide(self):
        self.pause_animation()
        self.canvas.itemconfigure(self.image_tag, state='hidden')

    def bind(self, *args, **kwargs):
        self.canvas.tag_bind(self.image_tag, *args, **kwargs)

    def unbind(self, *args, **kwargs):
        self.canvas.tag_unbind(self.image_tag, *args, **kwargs)

    def destroy(self):
        self.stop_animation()

        if self.image_tag is not None:
            try:
                self.canvas.delete(self.image_tag)
            except Exception:
                pass
            self.image_tag = None

        self.image = None
        self._image = None

        super().destroy()


class UIImageButton(UICanvasWidget, CTkBaseClass):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 x: int = 40,
                 y: int = 40,
                 width: int = 48,
                 height: int = 48,
                 anchor: str = 'center',
                 command: Callable = None,
                 disabled: bool = False,
                 # Background Image
                 bg_image_path: Optional[Union[Path, Image]] = None,
                 bg_width: int = 64,
                 bg_height: int = 64,
                 bg_normal_opacity: float = 1,
                 bg_hover_opacity: float = 1,
                 bg_selected_opacity: float = 1,
                 bg_disabled_opacity: float = 1,
                 bg_normal_brightness: float = 1,
                 bg_hover_brightness: float = 1,
                 bg_selected_brightness: float = 1,
                 bg_disabled_brightness: float = 1,
                 fg_color: Optional[Union[str, Tuple[str, str]]] = None,
                 border_radius: int = 0,
                 border_width: int = 0,
                 border_color: Optional[Union[str, Tuple[str, str]]] = None,
                 # Button Image
                 button_image_path: Optional[Union[Path, Image]] = None,
                 button_x_offset: int = 0,
                 button_y_offset: int = 0,
                 button_normal_opacity: float = 1,
                 button_hover_opacity: float = 1,
                 button_selected_opacity: float = 1,
                 button_disabled_opacity: float = 1,
                 button_normal_brightness: float = 1,
                 button_hover_brightness: float = 1,
                 button_selected_brightness: float = 1,
                 button_disabled_brightness: float = 1,
                 # Text
                 text: str = None,
                 font: str = 'Roboto 14',
                 justify: str = 'left',
                 text_x_offset: int = 0,
                 text_y_offset: int = 0,
                 text_anchor: str = None,
                 fill: str = 'black',
                 activefill: str = 'black',
                 disabledfill: str = 'black',
                 canvas=None,
                 auto_offset=None,
                 auto_offset_pad: int = 10,
                 **kwargs):

        CTkBaseClass.__init__(self, master=master)
        UIWidget.__init__(self, master, **kwargs)

        self.master = master
        self.canvas = canvas or master.canvas
        self.command = command
        self.disabled = disabled

        self._x = x
        self._y = y
        self._anchor = anchor
        self._button_x_offset = button_x_offset
        self._button_y_offset = button_y_offset
        self._text_x_offset = text_x_offset
        self._text_y_offset = text_y_offset

        self._bg_image = None
        if bg_image_path is not None or fg_color or border_radius:
            self._bg_image = self.put(UIImage(master=master, image_path=bg_image_path, width=bg_width, height=bg_height,
                                              x=x, y=y, anchor=anchor, opacity=bg_normal_opacity, brightness=bg_normal_brightness,
                                              fg_color=fg_color, border_radius=border_radius, border_width=border_width, border_color=border_color))
            self.bg_apply_normal = lambda: self._bg_image.configure(opacity=bg_normal_opacity, brightness=bg_normal_brightness)
            self.bg_apply_hover = lambda: self._bg_image.configure(opacity=bg_hover_opacity, brightness=bg_hover_brightness)
            self.bg_apply_select = lambda: self._bg_image.configure(opacity=bg_selected_opacity, brightness=bg_selected_brightness)
            self.bg_apply_disable = lambda: self._bg_image.configure(opacity=bg_disabled_opacity, brightness=bg_disabled_brightness)

        self._button_image = None
        if button_image_path is not None:
            self._button_image = self.put(UIImage(master=master, image_path=button_image_path, width=width, height=height,
                                                  x=button_x_offset+x, y=button_y_offset+y, anchor=anchor,
                                                  opacity=button_normal_opacity, brightness=button_normal_brightness))
            self.button_apply_normal = lambda: self._button_image.configure(opacity=button_normal_opacity, brightness=button_normal_brightness)
            self.button_apply_hover = lambda: self._button_image.configure(opacity=button_hover_opacity, brightness=button_hover_brightness)
            self.button_apply_select = lambda: self._button_image.configure(opacity=button_selected_opacity, brightness=button_selected_brightness)
            self.button_apply_disable = lambda: self._button_image.configure(opacity=button_disabled_opacity, brightness=button_disabled_brightness)

        self._text_image = None
        if text is not None:
            self._text_image = self.put(UIText(master=master, canvas=self.canvas, text=text, font=font, width=0, justify=justify,
                                               x=text_x_offset+x, y=text_y_offset+y, anchor=text_anchor or anchor,
                                               fill=fill, activefill=activefill, disabledfill=disabledfill))

        self.update_dimensions()

        self.hovered = False
        self.selected = False

        self._apply_theme()

        if auto_offset == 'center' and button_image_path is not None and text is not None:
            button_offset = -(self._text_image.winfo_width() + auto_offset_pad) / 2
            text_offset = +(self._button_image.winfo_width() + auto_offset_pad) / 2
            self._button_image.move(x=x+button_x_offset+button_offset, y=y+button_y_offset)
            self._text_image.move(x=x+text_x_offset+text_offset, y=y+text_y_offset)

        self.bind("<ButtonPress-1>", self._handle_button_press)
        self.bind("<ButtonRelease-1>", self._handle_button_release)
        self.bind("<Enter>", self._handle_enter)
        self.bind("<Leave>", self._handle_leave)

    def move(self, x=None, y=None):
        x = x or self._x
        y = y or self._y
        self._x = x
        self._y = y
        if self._bg_image is not None:
            self._bg_image.move(x, y)
        if self._button_image is not None:
            self._button_image.move(self._button_x_offset + x, self._button_y_offset + y)
        if self._text_image is not None:
            self._text_image.move(self._text_x_offset + x, self._text_y_offset + y)
        self.update_dimensions()

    def update_dimensions(self):
        x0, y0, x1, y1 = None, None, None, None

        for widget in [self._bg_image, self._button_image, self._text_image]:
            if widget is None:
                continue
            x0 = widget._x if x0 is None else min(x0, widget._x)
            y0 = widget._y if y0 is None else min(y0, widget._y)
            x1 = widget._x + widget._width if x1 is None else max(x1, widget._x + widget._width)
            y1 = widget._y + widget._height if y1 is None else max(y1, widget._y + widget._height)

        self._width = x1 - x0
        self._height = y1 - y0

    def set_text(self, text):
        self._text_image.set(text)
        self.update_dimensions()

    def bind(self, *args, **kwargs):
        for element in self.elements.values():
            element.bind(*args, **kwargs)

    def unbind(self, *args, **kwargs):
        for element in self.elements.values():
            element.unbind(*args, **kwargs)

    def _handle_button_press(self, event):
        if self.disabled:
            return
        if self.tooltip:
            self.tooltip.hide()
        self.set_selected(True)

    def _handle_button_release(self, event):
        if self.disabled:
            return
        self.set_selected(False)
        if self.hovered:
            self.command()

    def _handle_enter(self, event):
        self.hovered = True
        if self.disabled:
            self.set_disabled(self.disabled)
            return
        self.canvas.config(cursor="hand2")
        if self.selected:
            self.set_selected(self.selected)
        else:
            if self._bg_image:
                self.bg_apply_hover()
            if self._button_image:
                self.button_apply_hover()
        if self._text_image:
            self._text_image.force_active()

    def _handle_leave(self, event):
        self.hovered = False
        if self.disabled:
            self.set_disabled(self.disabled)
            return
        self.canvas.config(cursor="")
        if self.selected:
            self.set_selected(self.selected)
        else:
            if self._bg_image:
                self.bg_apply_normal()
            if self._button_image:
                self.button_apply_normal()
        if self._text_image:
            self._text_image.force_normal()

    def set_selected(self, selected: bool = False):
        self.selected = selected
        if selected:
            self.disabled = False
            if self._bg_image:
                self.bg_apply_select()
            if self._button_image:
                self.button_apply_select()
        else:
            if self.hovered:
                self._handle_enter(None)
            else:
                self._handle_leave(None)

    def set_disabled(self, disabled: bool = False):
        self.disabled = disabled
        if disabled:
            if self._bg_image:
                self.bg_apply_disable()
            if self._button_image:
                self.button_apply_disable()
            if self._text_image:
                self._text_image.force_disabled()
        else:
            if self.hovered:
                self._handle_enter(None)
            else:
                self._handle_leave(None)

    def _show(self):
        pass

    def _hide(self):
        pass

    def winfo_x(self):
        return int(self._apply_widget_scaling(self._x))

    def winfo_y(self):
        return int(self._apply_widget_scaling(self._y))

    def winfo_width(self):
        return int(self._apply_widget_scaling(self._width))

    def winfo_height(self):
        return int(self._apply_widget_scaling(self._height))

    def destroy(self):
        if self._bg_image:
            self._bg_image.destroy()
        if self._button_image:
            self._button_image.destroy()
        if self._text_image:
            self._text_image.destroy()
        super().destroy()


class UILabel(UIWidget, CTkLabel):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 image_path: Optional[Path] = None,
                 state: str = tkinter.NORMAL,
                 text_color_disabled: Optional[Union[str, Tuple[str, str]]] = None,
                 **kwargs):
        UIWidget.__init__(self, master, **kwargs)
        self._state = state
        self.image: Optional[CTkImage] = None
        if image_path is not None:
            self._supported_extensions = ['.webp', '.jpeg', '.png', '.jpg']
            self.image = CTkImage(Image.open(str(Config.get_resource_path(self, image_path, self._supported_extensions))))
        CTkLabel.__init__(self, master, image=self.image, **kwargs)

        if text_color_disabled is None:
            if "text_color_disabled" in ThemeManager.theme["CTkLabel"]:
                self._text_color_disabled = ThemeManager.theme["CTkLabel"]["text_color_disabled"]
            else:
                self._text_color_disabled = self._text_color
        else:
            self._text_color_disabled = self._check_color_type(text_color_disabled)

        self._apply_theme()

    def set(self, value):
        self.configure(text=value)

    def configure(self, require_redraw=False, **kwargs):
        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            require_redraw = True

        super().configure(require_redraw, **kwargs)

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border(self._apply_widget_scaling(self._current_width),
                                                                              self._apply_widget_scaling(self._current_height),
                                                                              self._apply_widget_scaling(self._corner_radius),
                                                                              0)
        if self._state == tkinter.DISABLED:
            text_color = self._text_color_disabled
        else:
            text_color = self._text_color

        if no_color_updates is False or requires_recoloring:
            if self._apply_appearance_mode(self._fg_color) == "transparent":
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(self._bg_color),
                                        outline=self._apply_appearance_mode(self._bg_color))

                self._label.configure(fg=self._apply_appearance_mode(text_color),
                                      disabledforeground=self._apply_appearance_mode(self._text_color_disabled),
                                      bg=self._apply_appearance_mode(self._bg_color))
            else:
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(self._fg_color),
                                        outline=self._apply_appearance_mode(self._fg_color))

                self._label.configure(fg=self._apply_appearance_mode(text_color),
                                      disabledforeground=self._apply_appearance_mode(self._text_color_disabled),
                                      bg=self._apply_appearance_mode(self._fg_color))

            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))


class ColorizedCTkImage(CTkImage):
    def __init__(
        self,
        template: Image.Image,
        color,
    ):
        self._template = template.convert("RGBA")
        self._color = color

        super().__init__(
            light_image=self._colorize(color),
            dark_image=self._colorize(color),
        )

    def _colorize(self, color):
        image = Image.new("RGBA", self._template.size, color)
        image.putalpha(self._template.getchannel("A"))
        return image

    def set_color(self, color):
        self._color = color

        light_image = self._colorize(color)
        dark_image = self._colorize(color)

        # Update CTkImage's source images without configure(),
        # because configure() invalidates the PhotoImage cache.
        self._light_image = light_image
        self._dark_image = dark_image

        # Update already-created PhotoImages in place.
        for size, photo in self._scaled_light_photo_images.items():
            photo.paste(light_image.resize(size))

        for size, photo in self._scaled_dark_photo_images.items():
            photo.paste(dark_image.resize(size))


class UIButton(UIWidget, CTkButton):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 image_path: Optional[Path] = None,
                 select_color: Optional[Union[str, Tuple[str, str]]] = None,
                 text_color_hovered: Optional[Union[str, Tuple[str, str]]] = None,
                 text_color_selected: Optional[Union[str, Tuple[str, str]]] = None,
                 fg_color_disabled: Optional[Union[str, Tuple[str, str]]] = None,
                 border_color_disabled: Optional[Union[str, Tuple[str, str]]] = None,
                 auto_width: bool = False,
                 padx: int = 12,
                 **kwargs):

        UIWidget.__init__(self, master, **kwargs)

        self._auto_width = auto_width
        self._padx = padx

        self._image_template = None
        self.image = None

        if image_path is not None:
            self._supported_extensions = ['.webp', '.jpeg', '.png', '.jpg']
            path = Config.get_resource_path(self, image_path, self._supported_extensions )

            self._image_template = Image.open(str(path)).convert("RGBA")

            self.image = ColorizedCTkImage(
                template=self._image_template,
                color="#ffffff",
            )

        self.is_hovered = False
        self.is_selected = False

        self._select_color: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["select_color"] if select_color is None else self._check_color_type(select_color)
        self._text_color_hovered: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["text_color_hovered"] if text_color_hovered is None else self._check_color_type(text_color_hovered)
        self._text_color_selected: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["text_color_selected"] if text_color_selected is None else self._check_color_type(text_color_selected)
        self._fg_color_disabled = ThemeManager.theme["CTkButton"].get("fg_color_disabled", None) if fg_color_disabled is None else self._check_color_type(fg_color_disabled)
        self._border_color_disabled = ThemeManager.theme["CTkButton"].get("border_color_disabled", None) if border_color_disabled is None else self._check_color_type(border_color_disabled)

        CTkButton.__init__(self, master, image=self.image, **kwargs)

        self._apply_theme()

        if self._auto_width:
            self._set_auto_width()

        self.unbind('<Button-1>')

    def tk_color_to_rgb(self, color):
        r, g, b = self.winfo_rgb(color)

        return (
            r // 256,
            g // 256,
            b // 256,
        )

    def configure(self, require_redraw=False, **kwargs):
        if 'select_color' in kwargs:
            self._select_color = self._check_color_type(kwargs.pop('select_color'))
            require_redraw = True
        if 'text_color_hovered' in kwargs:
            self._text_color_hovered = self._check_color_type(kwargs.pop('text_color_hovered'))
            require_redraw = True
        if 'text_color_selected' in kwargs:
            self._text_color_selected = self._check_color_type(kwargs.pop('text_color_selected'))
            require_redraw = True
        if 'fg_color_disabled' in kwargs:
            self._fg_color_disabled = self._check_color_type(kwargs.pop('fg_color_disabled'))
            require_redraw = True
        if 'border_color_disabled' in kwargs:
            self._border_color_disabled = self._check_color_type(kwargs.pop('border_color_disabled'))
            require_redraw = True

        require_auto_width = False

        if 'padx' in kwargs:
            self._padx = kwargs.pop('padx')
            require_auto_width = True

        if self._auto_width:
            if 'font' in kwargs or 'text' in kwargs:
                require_auto_width = True

        text_font = kwargs.get('font', None)
        if text_font is not None:
            kwargs['font'] = tuple(text_font)

        super().configure(require_redraw, **kwargs)

        if require_auto_width:
            self._set_auto_width()

    def get_text_width(self) -> int:
        return round(self._text_label.winfo_reqwidth() / self._apply_widget_scaling(1)) if self._text_label else 0

    def get_auto_width(self) -> int:
        scaling = self._apply_widget_scaling(1)
        offset = self._padx * 2
        if scaling != 1.0:
            offset += 2 * scaling
        return self.get_text_width() + round(offset)

    def _set_auto_width(self):
        self.configure(width=self.get_auto_width())

    def _get_visual_state_colors(self):
        """Return (border_color, text_color, inner_color) for the current state."""

        if self._state == tkinter.DISABLED:
            border_color = self._border_color_disabled if self._border_color_disabled is not None else self._border_color
            inner_color = self._fg_color_disabled if self._fg_color_disabled is not None else self._fg_color
            text_color = self._text_color_disabled

        elif self.is_hovered:
            border_color = self._border_color
            text_color = self._text_color_hovered
            inner_color = self._fg_color if self._hover_color is None else self._hover_color

        elif self.is_selected and not getattr(self, "_click_animation_running", False):
            border_color = self._border_color
            text_color = self._text_color_selected
            inner_color = self._select_color

        else:
            border_color = self._border_color
            text_color = self._text_color
            inner_color = self._fg_color

        # A transparent button should display its background color rather
        # than treating "transparent" as an actual canvas fill color.
        if inner_color == "transparent":
            inner_color = self._bg_color

        return border_color, text_color, inner_color

    def _get_current_text_color(self):
        """Return the text color for the current visual state."""
        return self._get_visual_state_colors()[1]

    def _update_image_color(self):
        if self.image is None:
            return

        color = self._get_current_text_color()

        if color is None:
            return

        # Resolve ("light", "dark") correctly.
        color = self._apply_appearance_mode(color)

        self.image.set_color(self.tk_color_to_rgb(color))

        self._image = self.image

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        if self._background_corner_colors is not None:
            self._draw_engine.draw_background_corners(
                self._apply_widget_scaling(self._current_width),
                self._apply_widget_scaling(self._current_height),
            )

            corner_tags = (
                "background_corner_top_left",
                "background_corner_top_right",
                "background_corner_bottom_right",
                "background_corner_bottom_left",
            )

            for tag, color in zip(corner_tags, self._background_corner_colors):
                self._canvas.itemconfig(tag, fill=self._apply_appearance_mode(color))
        else:
            self._canvas.delete("background_parts")

        # Resolve all state-dependent colors from the same source.
        border_color, text_color, inner_color = self._get_visual_state_colors()

        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border(
            self._apply_widget_scaling(self._current_width),
            self._apply_widget_scaling(self._current_height),
            self._apply_widget_scaling(self._corner_radius),
            self._apply_widget_scaling(self._border_width),
        )

        if not no_color_updates or requires_recoloring:
            self._update_image_color()
            self._configure_button_cursors()

            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

            resolved_border_color = self._apply_appearance_mode(border_color)
            resolved_inner_color = self._apply_appearance_mode(inner_color)

            # Border
            self._canvas.itemconfig("border_parts", outline=resolved_border_color, fill=resolved_border_color)

            # Background, including selected and hovered states.
            self._canvas.itemconfig("inner_parts", outline=resolved_inner_color, fill=resolved_inner_color)

        # Text label
        if self._text is not None and self._text != "":
            if self._text_label is None:
                self._text_label = tkinter.Label(
                    master=self,
                    font=self._apply_font_scaling(self._font),
                    text=self._text,
                    padx=0,
                    pady=0,
                    borderwidth=1,
                    textvariable=self._textvariable,
                )
                self._create_grid()

                self._text_label.bind("<Enter>", self._on_enter)
                self._text_label.bind("<Leave>", self._on_leave)
                self._text_label.bind("<Button-1>", self._clicked)

            if not no_color_updates:
                self._text_label.configure(
                    fg=self._apply_appearance_mode(text_color),
                    bg=self._apply_appearance_mode(inner_color),
                )

        elif self._text_label is not None:
            self._text_label.destroy()
            self._text_label = None
            self._create_grid()

        # Image label
        if self._image is not None:
            if self._image_label is None:
                self._image_label = tkinter.Label(master=self)
                self._update_image()
                self._create_grid()

                self._image_label.bind("<Enter>", self._on_enter)
                self._image_label.bind("<Leave>", self._on_leave)
                self._image_label.bind("<Button-1>", self._clicked)

            if not no_color_updates:
                self._image_label.configure(
                    bg=self._apply_appearance_mode(inner_color)
                )

        elif self._image_label is not None:
            self._image_label.destroy()
            self._image_label = None
            self._create_grid()

    def _update_visual_state(self):
        """Apply the current visual state without redrawing the widget."""

        _, text_color, inner_color = self._get_visual_state_colors()

        text_color = self._apply_appearance_mode(text_color) if text_color is not None else None
        inner_color = self._apply_appearance_mode(inner_color)

        # Button background
        self._canvas.itemconfig("inner_parts", outline=inner_color, fill=inner_color)

        # Text
        if self._text_label is not None:
            self._text_label.configure(fg=text_color, bg=inner_color)

        # Image background
        if self._image_label is not None:
            self._image_label.configure(bg=inner_color)

        # Keep image tint synchronized with the text color.
        if self.image is not None and text_color is not None:
            self.image.set_color(self.tk_color_to_rgb(text_color))
            self._image = self.image

    def _on_enter(self, event=None):
        self.is_hovered = True

        if self._state == tkinter.DISABLED:
            return

        self._update_visual_state()

    def _configure_button_cursors(self):
        if not self._cursor_manipulation_enabled:
            return

        if self._state == tkinter.NORMAL and self._command is not None:
            if sys.platform == "darwin":
                cursor = "pointinghand"
            elif sys.platform.startswith("win"):
                cursor = "hand2"
            else:
                cursor = "arrow"
        else:
            cursor = "arrow"

        self._canvas.configure(cursor=cursor)

        if self._text_label is not None:
            self._text_label.configure(cursor=cursor)

        if self._image_label is not None:
            self._image_label.configure(cursor=cursor)

    def _on_leave(self, event=None):
        self.is_hovered = False

        if self._state == tkinter.DISABLED:
            return

        self._click_animation_running = False

        self._update_visual_state()

    def _clicked(self, event=None):
        if not self.is_hovered:
            return
        super()._clicked(event)

    def _create_bindings(self, sequence: Optional[str] = None):
        if sequence == "<Button-1>":
            self.bind('<ButtonRelease-1>', self._clicked)
            return
        super()._create_bindings(sequence)

    def set_selected(self, selected: bool = False):
        self.is_selected = selected
        self._update_visual_state()


class UIRadioButton(UIWidget, CTkRadioButton):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):

        UIWidget.__init__(self, master, **kwargs)

        CTkRadioButton.__init__(self, master, **kwargs)

        self._apply_theme()


class UIProgressBar(UIWidget, CTkProgressBar):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):

        UIWidget.__init__(self, master, **kwargs)
        CTkProgressBar.__init__(self, master, **kwargs)

        self._apply_theme()


class UIEntry(CTkEntry, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 input_filter: Optional[str] = None,
                 fg_color_disabled: Optional[Union[str, Tuple[str, str]]] = None,
                 border_color_disabled: Optional[Union[str, Tuple[str, str]]] = None,
                 text_color_disabled: Optional[Union[str, Tuple[str, str]]] = None,
                 **kwargs):

        self._entry_right_offset = 0

        UIWidget.__init__(self, master, **kwargs)

        # Smart input filtering for INT and FLOAT values
        self._input_filter = input_filter.upper() if input_filter else None
        if self._input_filter is not None:
            self.setup_input_filter(master, kwargs)

        self._fg_color_disabled = ThemeManager.theme["CTkEntry"].get("fg_color_disabled", None) if fg_color_disabled is None else self._check_color_type(fg_color_disabled)
        self._border_color_disabled = ThemeManager.theme["CTkEntry"].get("border_color_disabled", None) if border_color_disabled is None else self._check_color_type(border_color_disabled)
        self._text_color_disabled = ThemeManager.theme["CTkEntry"].get("text_color_disabled", None) if text_color_disabled is None else self._check_color_type(text_color_disabled)

        CTkEntry.__init__(self, master, **kwargs)

        self.state_log = [('', 0)]
        self.state_id = -1

        self.bind("<Key>", self.initialize_state_log)
        self.bind("<Control-KeyPress>", self.handle_key_press)
        self.bind("<KeyRelease>", self.add_state)
        self.bind("<<Cut>>", lambda event: self.after(200, self.add_state))
        self.bind("<Button-3>", self.handle_button3)
        self.bind("<<Paste>>", self.paste_to_selection)
        self.bind("<Return>", self.handle_return)

        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.config(font=self._apply_font_scaling(('Asap', 14)))
        self.context_menu.add_command(label="Cut")
        self.context_menu.add_command(label="Copy")
        self.context_menu.add_command(label="Paste")

        self._apply_theme()

    @staticmethod
    def validate_float_like_input(value):
        if value == '':
            return True
        return re.fullmatch(r'^-?(\d+)?(\.\d*)?$', value) is not None

    @staticmethod
    def validate_int_like_input(value):
        if value == '':
            return True
        return re.fullmatch(r'^-?\d*$', value) is not None

    def setup_input_filter(self, master, kwargs):
        self._textvariable = None
        self._original_textvariable = kwargs.pop('textvariable', None)
        if self._original_textvariable is None:
            return

        proxy_var = StringVar(master=master, value=f'{self._original_textvariable.get()}')

        proxy_var.trace_add('write', self.handle_proxy_var_update)
        self.trace_write(self._original_textvariable, self.handle_original_var_update)

        kwargs['textvariable'] = proxy_var

        kwargs['validate'] = 'key'
        if self._input_filter == 'INT':
            kwargs['validatecommand'] = (master.register(self.validate_int_like_input), "%P")
        elif self._input_filter == 'FLOAT':
            kwargs['validatecommand'] = (master.register(self.validate_float_like_input), "%P")
        else:
            raise ValueError(f'Unknown input filer type `{self._input_filter}`!')

    def _get_proxy_var_value(self):
        value = self._textvariable.get()
        if value in ['', '-', '.']:
            value = 0
        if self._input_filter == 'INT':
            return int(value)
        elif self._input_filter == 'FLOAT':
            return float(value)
        else:
            raise ValueError(f'Unknown input filer type `{self._input_filter}`!')

    def handle_original_var_update(self, var, original_val):
        if self._textvariable is None:
            return
        value = self._get_proxy_var_value()
        if value != self._original_textvariable.get():
            self._original_textvariable.set(value)

    def handle_proxy_var_update(self, varname=None, index=None, mode=None):
        value = self._get_proxy_var_value()
        if value != self._original_textvariable.get():
            self._original_textvariable.set(value)

    def _entry_focus_out(self, event=None):
        if self._input_filter is not None:
            value = self._get_proxy_var_value()
            self.set(value)

        super()._entry_focus_out(event)

    def configure(self, require_redraw=False, **kwargs):
        if "state" in kwargs:
            require_redraw = True

        if 'fg_color_disabled' in kwargs:
            self._fg_color_disabled = self._check_color_type(kwargs.pop('fg_color_disabled'))
            require_redraw = True
        if 'border_color_disabled' in kwargs:
            self._border_color_disabled = self._check_color_type(kwargs.pop('border_color_disabled'))
            require_redraw = True
        if 'text_color_disabled' in kwargs:
            self._text_color_disabled = self._check_color_type(kwargs.pop('text_color_disabled'))
            require_redraw = True

        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)

        super().configure(require_redraw=require_redraw, **kwargs)

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border(self._apply_widget_scaling(self._current_width),
                                                                              self._apply_widget_scaling(self._current_height),
                                                                              self._apply_widget_scaling(self._corner_radius),
                                                                              self._apply_widget_scaling(self._border_width))

        if requires_recoloring or no_color_updates is False:
            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

            if self._apply_appearance_mode(self._fg_color) == "transparent":
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(self._bg_color),
                                        outline=self._apply_appearance_mode(self._bg_color))
                self._entry.configure(bg=self._apply_appearance_mode(self._bg_color),
                                      disabledbackground=self._apply_appearance_mode(self._bg_color),
                                      readonlybackground=self._apply_appearance_mode(self._bg_color),
                                      highlightcolor=self._apply_appearance_mode(self._bg_color))
            else:
                fg_color = self._fg_color
                if self._state == tkinter.DISABLED and self._fg_color_disabled:
                    fg_color = self._fg_color_disabled
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(fg_color),
                                        outline=self._apply_appearance_mode(fg_color))
                self._entry.configure(bg=self._apply_appearance_mode(fg_color),
                                      disabledbackground=self._apply_appearance_mode(fg_color),
                                      readonlybackground=self._apply_appearance_mode(fg_color),
                                      highlightcolor=self._apply_appearance_mode(fg_color))

            border_color = self._border_color
            if self._state == tkinter.DISABLED and self._border_color_disabled:
                border_color = self._border_color_disabled

            self._canvas.itemconfig("border_parts",
                                    fill=self._apply_appearance_mode(border_color),
                                    outline=self._apply_appearance_mode(border_color))

            if self._placeholder_text_active:
                self._entry.config(fg=self._apply_appearance_mode(self._placeholder_text_color),
                                   disabledforeground=self._apply_appearance_mode(self._placeholder_text_color),
                                   insertbackground=self._apply_appearance_mode(self._placeholder_text_color))
            else:
                text_color = self._text_color
                if self._state == tkinter.DISABLED and self._text_color_disabled:
                    text_color = self._text_color_disabled

                self._entry.config(fg=self._apply_appearance_mode(text_color),
                                   disabledforeground=self._apply_appearance_mode(text_color),
                                   insertbackground=self._apply_appearance_mode(text_color))

    def event_generate(self, *args, **kwargs):
        self._entry.event_generate(*args, **kwargs)

    def handle_key_press(self, event):
        if event.keycode == 65 and event.keysym.lower() != 'a':
            event.widget.event_generate("<<SelectAll>>")
        elif event.keycode == 67 and event.keysym.lower() != 'c':
            event.widget.event_generate("<<Copy>>")
        elif event.keycode == 86 and event.keysym.lower() != 'v':
            event.widget.event_generate("<<Paste>>")
        elif event.keycode == 88 and event.keysym.lower() != 'x':
            event.widget.event_generate("<<Cut>>")
        elif event.keycode == 89:
            self.redo()
        elif event.keycode == 90:
            self.undo()
        elif event.keycode == 65535:
            event.widget.event_generate("<<Clear>>")

    def destroy(self):
        # Remove default write-trace callback for textvariable if exists
        if not (self._textvariable is None or self._textvariable == ""):
            self._textvariable.trace_vdelete('w', self._textvariable_callback_name)
        super().destroy()

    def set(self, value):
        self.delete(0, END)
        self.insert(0, value)

    def handle_button3(self, event=None):
        self.initialize_state_log()
        self.show_context_menu(event)

    def handle_return(self, event):
        self.master.focus_set()

    def initialize_state_log(self, event=None):
        if len(self.state_log) == 1:
            self.state_log[0] = (self.get(), self.index(INSERT))
            self.state_id = 0
            # print(f'INIT STATE: {self.state_log}')
        else:
            self.set_state(self.state_id, None, self.index(INSERT))

    def get_state(self, state_id: int = None):
        if state_id is None:
            state_id = self.state_id
        return self.state_log[state_id][0]

    def get_index_after_state(self, state_id: int = None):
        if state_id is None:
            state_id = self.state_id
        return self.state_log[state_id][1]

    def set_state(self, state_id, value=None, index=None):
        if state_id < len(self.state_log):
            state = self.state_log[state_id]
            self.state_log[state_id] = (value or state[0], index or state[1])
        else:
            self.state_log.append((value, index))

    def add_state(self, event=None):
        if len(self.state_log) > 0:
            if self.get() == self.get_state():
                # print(f'NO CHANGES: {self.state_log}')
                return

            old_states = self.state_log[self.state_id:]
            # print(f'REMOVE: {old_states}  STATES: {self.state_log}')
            self.state_log = self.state_log[:self.state_id + 1]

        self.state_id = len(self.state_log)
        self.set_state(self.state_id, self.get(), self.index(INSERT))
        # print(f'ADD State {self.state_id} ({self.get_state()}) STATES: {self.state_log}')

    def paste_to_selection(self, event):
        clipboard = ''
        try:
            clipboard = event.widget.clipboard_get()
        except:
            pass
        if not clipboard:
            return 'break'
        self.initialize_state_log()
        try:
            event.widget.delete('sel.first', 'sel.last')
        except:
            pass
        event.widget.insert('insert', clipboard)
        self.add_state()
        return 'break'

    def undo(self, event=None):
        new_state_id = self.state_id - 1
        # print(f'UNDO: State {self.state_id} -> {new_state_id} / {len(self.state_log)} ({self.get_state()} -> {self.get_state(new_state_id)})')
        if new_state_id >= 0:
            # print(f'SET: {self.get_state(new_state_id)} INDEX {self.get_index_after_state(new_state_id)}')
            self.set(self.get_state(new_state_id))
            self.icursor(self.get_index_after_state(new_state_id))
            self.state_id = new_state_id

    def redo(self, event=None):
        new_state_id = self.state_id + 1
        # print(f'REDO: State {self.state_id} -> {new_state_id} / {len(self.state_log)} ({self.get_state()})')
        if new_state_id < len(self.state_log):
            # print(f'SET: {self.get_state(new_state_id)} INDEX {self.get_index_after_state(new_state_id)}')
            self.set(self.get_state(new_state_id))
            self.icursor(self.get_index_after_state(new_state_id))
            self.state_id = new_state_id

    def show_context_menu(self, event):
        if self._state != tkinter.DISABLED:
            self.context_menu.post(event.x_root, event.y_root)
            self.context_menu.entryconfigure('Cut', command=lambda: self.event_generate('<<Cut>>'))
            self.context_menu.entryconfigure('Copy', command=lambda: self.event_generate('<<Copy>>'))
            self.context_menu.entryconfigure('Paste', command=lambda: self.event_generate('<<Paste>>'))

    def set_right_offset(self, right_offset: int):
        self._entry_right_offset = right_offset
        self._create_grid()

    def _create_grid(self):
        self._canvas.grid(column=0, row=0, sticky="nswe")

        if self._corner_radius >= self._minimum_x_padding:
            pad_x = min(self._apply_widget_scaling(self._corner_radius), round(self._apply_widget_scaling(self._current_height / 2)))
            self._entry.grid(column=0, row=0, sticky="nswe",
                             padx=(pad_x, pad_x + round(self._apply_widget_scaling(self._entry_right_offset))),
                             pady=(self._apply_widget_scaling(self._border_width),
                                   self._apply_widget_scaling(self._border_width + 1)))
        else:
            pad_x = self._apply_widget_scaling(self._minimum_x_padding)
            self._entry.grid(column=0, row=0, sticky="nswe",
                             padx=(pad_x, pad_x + round(self._apply_widget_scaling(self._entry_right_offset))),
                             pady=(self._apply_widget_scaling(self._border_width),
                                   self._apply_widget_scaling(self._border_width + 1)))


class UICheckbox(CTkCheckBox, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):
        UIWidget.__init__(self, master, **kwargs)

        self._fg_color_disabled = ThemeManager.theme["CTkCheckBox"].get("fg_color_disabled", None)
        self._checkmark_color_disabled = ThemeManager.theme["CTkCheckBox"].get("checkmark_color_disabled", None)
        self._border_color_disabled = ThemeManager.theme["CTkCheckBox"].get("border_color_disabled", None)
        self._text_color_checked = ThemeManager.theme["CTkCheckBox"].get("text_color_checked", None)

        self.is_hovered = False

        self._text_color_hovered = None
        if 'text_color_hovered' in kwargs:
            self._text_color_hovered = kwargs.pop('text_color_hovered')

        CTkCheckBox.__init__(self, master, **kwargs)

        if not self._text_color_hovered:
            self._text_color_hovered = self._text_color

        self._apply_theme()

        self.unbind('<Button-1>')

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        requires_recoloring_1 = self._draw_engine.draw_rounded_rect_with_border(self._apply_widget_scaling(self._checkbox_width),
                                                                                self._apply_widget_scaling(self._checkbox_height),
                                                                                self._apply_widget_scaling(self._corner_radius),
                                                                                self._apply_widget_scaling(self._border_width))

        if self._check_state is True:
            requires_recoloring_2 = self._draw_engine.draw_checkmark(self._apply_widget_scaling(self._checkbox_width),
                                                                     self._apply_widget_scaling(self._checkbox_height),
                                                                     self._apply_widget_scaling(self._checkbox_height * 0.5))
        else:
            requires_recoloring_2 = False
            self._canvas.delete("checkmark")

        if no_color_updates is False or requires_recoloring_1 or requires_recoloring_2:
            self._bg_canvas.configure(bg=self._apply_appearance_mode(self._bg_color))
            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

            if self._check_state is True:
                fg_color = self._fg_color
                if self._state == tkinter.DISABLED and self._fg_color_disabled:
                    fg_color = self._fg_color_disabled
                if self.is_hovered:
                    self._canvas.itemconfig("inner_parts",
                                            outline=self._apply_appearance_mode(self._hover_color),
                                            fill=self._apply_appearance_mode(self._hover_color))
                else:
                    self._canvas.itemconfig("inner_parts",
                                            outline=self._apply_appearance_mode(fg_color),
                                            fill=self._apply_appearance_mode(fg_color))
                # self._canvas.itemconfig("border_parts",
                #                         outline=self._apply_appearance_mode(fg_color),
                #                         fill=self._apply_appearance_mode(fg_color))
                if self._state == tkinter.DISABLED:
                    self._canvas.itemconfig("checkmark", fill=self._apply_appearance_mode(self._checkmark_color_disabled))
                else:
                    self._canvas.itemconfig("checkmark", fill=self._apply_appearance_mode(self._checkmark_color))
            else:
                self._canvas.itemconfig("inner_parts",
                                        outline=self._apply_appearance_mode(self._bg_color),
                                        fill=self._apply_appearance_mode(self._bg_color))

            self._text_label.configure(bg=self._apply_appearance_mode(self._bg_color))

            self._update_visual_state()

    def _update_visual_state(self):
        if self._state == tkinter.DISABLED:
            text_color = self._text_color_disabled
        elif self.is_hovered and self._text_color_hovered:
            text_color = self._text_color_hovered
        elif self._check_state and self._text_color_checked:
            text_color = self._text_color_checked
        else:
            text_color = self._text_color

        if self._state == tkinter.DISABLED:
            border_color = self._border_color_disabled
        else:
            border_color = self._border_color

        text_color = self._apply_appearance_mode(text_color)
        border_color = self._apply_appearance_mode(border_color)

        self._text_label.configure(fg=text_color)
        self._canvas.itemconfig("border_parts", outline=border_color, fill=border_color)

    def set(self, value):
        if value == self._onvalue:
            self.select()
        elif value == self._offvalue:
            self.deselect()
        else:
            raise ValueError(f'Failed to set checkbox to unknown value {value}!')

        self.unbind('<Button-1>')

    def configure(self, require_redraw=False, **kwargs):
        if 'text_color_hovered' in kwargs:
            self._text_color_hovered = self._check_color_type(kwargs.pop('text_color_hovered'))
            require_redraw = True
        if 'text_color_checked' in kwargs:
            self._text_color_checked = self._check_color_type(kwargs.pop('text_color_checked'))
            require_redraw = True

        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)

        super().configure(require_redraw, **kwargs)

    def _on_enter(self, event=None):
        self.is_hovered = True
        self._set_cursor()
        if self._state == tkinter.DISABLED:
            return
        super()._on_enter(event)
        self._update_visual_state()

    def _on_leave(self, event=None):
        self.is_hovered = False
        self._set_cursor()
        if self._state == tkinter.DISABLED:
            return
        super()._on_leave(event)
        self._update_visual_state()

    def toggle(self, event=0):
        if not self.is_hovered:
            return
        super().toggle(event)

    def _create_bindings(self, sequence: Optional[str] = None):
        if sequence == "<Button-1>":
            self.bind('<ButtonRelease-1>', self.toggle)
            return
        super()._create_bindings(sequence)

    def _set_cursor(self):
        if self._cursor_manipulation_enabled:
            if not self.is_hovered or self._state == tkinter.DISABLED:
                if sys.platform == "darwin":
                    self._canvas.configure(cursor="arrow")
                    if self._text_label is not None:
                        self._text_label.configure(cursor="arrow")
                elif sys.platform.startswith("win"):
                    self._canvas.configure(cursor="arrow")
                    if self._text_label is not None:
                        self._text_label.configure(cursor="arrow")

            else:
                if sys.platform == "darwin":
                    self._canvas.configure(cursor="pointinghand")
                    if self._text_label is not None:
                        self._text_label.configure(cursor="pointinghand")
                elif sys.platform.startswith("win"):
                    self._canvas.configure(cursor="hand2")
                    if self._text_label is not None:
                        self._text_label.configure(cursor="hand2")


class UIOptionMenu(CTkOptionMenu, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):
        UIWidget.__init__(self, master, **kwargs)
        if isinstance(kwargs.get('values', None), dict):
            self._setup_values(master, kwargs)
        self._border_width = ThemeManager.theme["CTkTextbox"].get("border_width", 2)
        self._button_color_disabled = ThemeManager.theme["CTkOptionMenu"].get("button_color_disabled", None)
        CTkOptionMenu.__init__(self, master, **kwargs)
        self.dropdown_menu_opened = False
        self.dropdown_menu_close_time = 0

        self._apply_theme()

    def configure(self, require_redraw=False, **kwargs):
        if 'border_width' in kwargs:
            self._border_width = self._check_color_type(kwargs.pop('border_width'))
            require_redraw = True

        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)

        super().configure(require_redraw, **kwargs)

    def _setup_values(self, master, kwargs):
        self._values_dict = kwargs.pop('values')
        self._variable = None
        self._original_variable = kwargs.pop('variable', None)

        proxy_var = StringVar(master=master, value=f'{self._values_dict[self._original_variable.get()]}')

        proxy_var.trace_add('write', self._handle_proxy_var_update)
        self.trace_write(self._original_variable, self._handle_original_var_update)

        kwargs['variable'] = proxy_var
        kwargs['values'] = list(self._values_dict.values())

    def get(self) -> str:
        if self._values_dict is None:
            return self._current_value
        else:
            return next((k for k, v in self._values_dict.items() if v == self._current_value), None)

    def _handle_original_var_update(self, var, original_val):
        if self._variable is None:
            return
        value = self._values_dict[self._original_variable.get()]
        if value != self._variable.get():
            self._variable.set(value)

    def _handle_proxy_var_update(self, varname=None, index=None, mode=None):
        value = self._variable.get()
        value_key = next((k for k, v in self._values_dict.items() if v == value), None)
        if value_key != self._original_variable.get():
            self._original_variable.set(value_key)

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        left_section_width = self._current_width - self._current_height
        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border_vertical_split(self._apply_widget_scaling(self._current_width),
                                                                                             self._apply_widget_scaling(self._current_height),
                                                                                             self._apply_widget_scaling(self._corner_radius),
                                                                                             self._apply_widget_scaling(self._border_width),
                                                                                             self._apply_widget_scaling(left_section_width))

        # Drawing Y with CustomTkinter_shapes_font bugs out for some reason, lets hardcode ▼ for now
        requires_recoloring_2 = False

        x_position = self._apply_widget_scaling(self._current_width - (self._current_height / 2))
        y_position = self._apply_widget_scaling(self._current_height / 2)
        size = self._apply_widget_scaling(self._current_height / 3)

        x_position, y_position, size = round(x_position), round(y_position), round(size)

        if not self._canvas.find_withtag("dropdown_arrow"):
            self._canvas.create_text(0, 0, text="▼", font=("Arial", -size), tags="dropdown_arrow",
                                     anchor=tkinter.CENTER)
            self._canvas.tag_raise("dropdown_arrow")
            requires_recoloring = True

        self._canvas.itemconfigure("dropdown_arrow", font=("Arial", -size))
        self._canvas.coords("dropdown_arrow", x_position, y_position)

        if no_color_updates is False or requires_recoloring or requires_recoloring_2:
            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

            self._canvas.itemconfig("inner_parts_left",
                                    outline=self._apply_appearance_mode(self._fg_color),
                                    fill=self._apply_appearance_mode(self._fg_color))

            self._text_label.configure(fg=self._apply_appearance_mode(self._text_color))

            if self._state == tkinter.DISABLED:
                self._canvas.itemconfig("inner_parts_right",
                                        outline=self._apply_appearance_mode(self._button_color_disabled or self._button_color),
                                        fill=self._apply_appearance_mode(self._button_color_disabled or self._button_color))
                self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_disabled)))
                self._canvas.itemconfig("dropdown_arrow",
                                        fill=self._apply_appearance_mode(self._fg_color))
                self._canvas.itemconfig("border_parts",
                                        outline=self._apply_appearance_mode(self._button_color_disabled or self._button_color),
                                        fill=self._apply_appearance_mode(self._button_color_disabled or self._button_color))
            else:
                self._canvas.itemconfig("inner_parts_right",
                                        outline=self._apply_appearance_mode(self._button_color),
                                        fill=self._apply_appearance_mode(self._button_color))
                self._text_label.configure(fg=self._apply_appearance_mode(self._text_color))
                self._canvas.itemconfig("dropdown_arrow",
                                        fill=self._apply_appearance_mode(self._fg_color))
                self._canvas.itemconfig("border_parts",
                                        outline=self._apply_appearance_mode(self._button_color),
                                        fill=self._apply_appearance_mode(self._button_color))

            self._text_label.configure(bg=self._apply_appearance_mode(self._fg_color))


        self._canvas.update_idletasks()

    def _on_leave(self, event=0):
        # set color of inner button parts
        if self._state == tkinter.DISABLED:
            self._canvas.itemconfig("inner_parts_right",
                                    outline=self._apply_appearance_mode(self._button_color_disabled),
                                    fill=self._apply_appearance_mode(self._button_color_disabled))
        else:
            self._canvas.itemconfig("inner_parts_right",
                                    outline=self._apply_appearance_mode(self._button_color),
                                    fill=self._apply_appearance_mode(self._button_color))

    def _clicked(self, event=0):
        if self._state is not tkinter.DISABLED and len(self._values) > 0:
            if self.tooltip:
                self.tooltip._on_leave()
            if not self.dropdown_menu_opened:
                # Adding toggle behaviour to dropdown button is a bit tricky
                # By default, the same click that closes the menu will open it again if dropdown button is clicked
                # Also, as _open_dropdown_menu() is blocking, we can't directly check if menu is shown
                # So we'll use a timer to distinguish closing clicks from opening ones
                # World record is less than 20 CPS (~0.05 between clicks), so 5 times smaller interval should be fine
                if time.time() - self.dropdown_menu_close_time < 0.01:
                    return
                self._open_dropdown_menu()
            else:
                self._close_dropdown_menu()

    def _open_dropdown_menu(self):
        self.dropdown_menu_opened = True
        # Following call is blocking until the menu is closed
        super()._open_dropdown_menu()
        self.dropdown_menu_opened = False
        self.dropdown_menu_close_time = time.time()

    def _close_dropdown_menu(self):
        self._dropdown_menu.unpost()

    def _dropdown_callback(self, value: str):
        super()._dropdown_callback(value)

    def destroy(self):
        dropdown = getattr(self, '_dropdown_menu', None)

        if dropdown is not None:
            # Remove it from CustomTkinter's scaling callbacks.
            CTkScalingBaseClass.destroy(dropdown)

            # Destroy the actual Tk Menu.
            dropdown.destroy()

            self._dropdown_menu = None

        super().destroy()


class UITextbox(CTkTextbox, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 text_variable,
                 **kwargs):
        UIWidget.__init__(self, master, **kwargs)

        self._state = tkinter.NORMAL

        self._fg_color_disabled = ThemeManager.theme["CTkTextbox"].get("fg_color_disabled", None)
        self._border_color_disabled = ThemeManager.theme["CTkTextbox"].get("border_color_disabled", None)
        self._text_color_disabled = ThemeManager.theme["CTkTextbox"].get("text_color_disabled", None)

        CTkTextbox.__init__(self, master, **kwargs)

        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.config(font=self._apply_font_scaling(('Asap', 14)))
        self.context_menu.add_command(label="Cut")
        self.context_menu.add_command(label="Copy")
        self.context_menu.add_command(label="Paste")

        self.text_variable = text_variable

        self._apply_theme()

        self.trace_write(text_variable, self.handle_text_variable_update)
        self.bind("<Control-KeyPress>", self.handle_key_press)
        self.bind('<KeyRelease>', self.handle_on_widget_change)
        self.bind("<Button-3>", self.handle_button3)

    def configure(self, require_redraw=False, **kwargs):
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            self._textbox.configure(state=self._state)
            require_redraw = True

        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)

        super().configure(require_redraw=require_redraw, **kwargs)

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        if not self._canvas.winfo_exists():
            return

        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border(self._apply_widget_scaling(self._current_width),
                                                                              self._apply_widget_scaling(self._current_height),
                                                                              self._apply_widget_scaling(self._corner_radius),
                                                                              self._apply_widget_scaling(self._border_width))

        if no_color_updates is False or requires_recoloring:
            text_color = self._text_color
            if self._state == tkinter.DISABLED and self._text_color_disabled:
                text_color = self._text_color_disabled

            if self._fg_color == "transparent":
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(self._bg_color),
                                        outline=self._apply_appearance_mode(self._bg_color))
                self._textbox.configure(fg=self._apply_appearance_mode(text_color),
                                        bg=self._apply_appearance_mode(self._bg_color),
                                        insertbackground=self._apply_appearance_mode(text_color))
                self._x_scrollbar.configure(fg_color=self._bg_color, button_color=self._scrollbar_button_color,
                                            button_hover_color=self._scrollbar_button_hover_color)
                self._y_scrollbar.configure(fg_color=self._bg_color, button_color=self._scrollbar_button_color,
                                            button_hover_color=self._scrollbar_button_hover_color)
            else:
                fg_color = self._fg_color
                if self._state == tkinter.DISABLED and self._fg_color_disabled:
                    fg_color = self._fg_color_disabled

                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(fg_color),
                                        outline=self._apply_appearance_mode(fg_color))
                self._textbox.configure(fg=self._apply_appearance_mode(text_color),
                                        bg=self._apply_appearance_mode(fg_color),
                                        insertbackground=self._apply_appearance_mode(text_color))
                self._x_scrollbar.configure(fg_color=fg_color, button_color=self._scrollbar_button_color,
                                            button_hover_color=self._scrollbar_button_hover_color)
                self._y_scrollbar.configure(fg_color=fg_color, button_color=self._scrollbar_button_color,
                                            button_hover_color=self._scrollbar_button_hover_color)

            border_color = self._border_color
            if self._state == tkinter.DISABLED and self._border_color_disabled:
                border_color = self._border_color_disabled

            self._canvas.itemconfig("border_parts",
                                    fill=self._apply_appearance_mode(border_color),
                                    outline=self._apply_appearance_mode(border_color))
            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

        self._canvas.tag_lower("inner_parts")
        self._canvas.tag_lower("border_parts")

    def set(self, value):
        self.delete("1.0", END)
        self.insert("1.0", value)

    def handle_on_widget_change(self, event=None):
        self.text_variable.set(self.get(0.0, END))

    def handle_text_variable_update(self, var, val):
        if val != self.get(0.0, END):
            self.set(val)

    def handle_key_press(self, event):
        if event.keycode == 65 and event.keysym.lower() != 'a':
            event.widget.event_generate("<<SelectAll>>")
        elif event.keycode == 67 and event.keysym.lower() != 'c':
            event.widget.event_generate("<<Copy>>")
        elif event.keycode == 86 and event.keysym.lower() != 'v':
            event.widget.event_generate("<<Paste>>")
        elif event.keycode == 88 and event.keysym.lower() != 'x':
            event.widget.event_generate("<<Cut>>")
        elif event.keycode == 89 and event.keysym.lower() != 'y':
            event.widget.event_generate("<<Redo>>")
        elif event.keycode == 90 and event.keysym.lower() != 'z':
            event.widget.event_generate("<<Undo>>")
        elif event.keycode == 65535:
            event.widget.event_generate("<<Clear>>")

    def handle_button3(self, event=None):
        self.show_context_menu(event)

    def show_context_menu(self, event):
        if self._state != tkinter.DISABLED:
            self.context_menu.post(event.x_root, event.y_root)
            self.context_menu.entryconfigure('Cut', command=lambda: self._textbox.event_generate('<<Cut>>'))
            self.context_menu.entryconfigure('Copy', command=lambda: self._textbox.event_generate('<<Copy>>'))
            self.context_menu.entryconfigure('Paste', command=lambda: self._textbox.event_generate('<<Paste>>'))

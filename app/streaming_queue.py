__module_name__ = "streaming_queue"

"""
Streaming Queue Implementation for DoqToq

This module implements a producer-consumer pattern for smooth streaming animations
in Streamlit, acting as a "shock absorber" between fast LLM responses and
controlled UI animations.
"""

import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Iterator, Optional, Union
from venv import logger

from streamlit.delta_generator import DeltaGenerator


class LaTeXDebugLogger:
    """Smart logger that only captures LaTeX-related streaming events"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.log_file = None
        self.in_latex_context = False
        self.latex_start_char = 0
        self.context_buffer: list[str] = []  # Buffer for context around LaTeX
        self.max_context = 10  # Characters before/after LaTeX to log

        if self.enabled:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = open(
                f"./logs/latex_streaming_debug_{timestamp}.log", "w", encoding="utf-8"
            )
            self.log("=== LaTeX Streaming Debug Session Started ===\n")

    def log(self, message: str) -> None:
        """Write message to log file"""
        if self.enabled and self.log_file:
            self.log_file.write(
                f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {message}\n"
            )
            self.log_file.flush()

    def should_log_char(self, char: str, char_index: int) -> bool:
        """Determine if we should log this character based on LaTeX context"""
        if not self.enabled:
            return False

        # Start logging when we encounter $ or are already in LaTeX context
        if char == "$" or self.in_latex_context:
            if not self.in_latex_context:
                self.in_latex_context = True
                self.latex_start_char = char_index
                # Log some context before LaTeX
                self.log(f"--- LATEX CONTEXT START (char {char_index}) ---")
                if self.context_buffer:
                    context = "".join(self.context_buffer[-self.max_context :])
                    self.log(f"Context before: '{context}'")
            return True

        # Keep logging for a few characters after LaTeX ends
        if (
            hasattr(self, "latex_end_char")
            and char_index <= self.latex_end_char + self.max_context
        ):
            return True

        # Buffer context for potential LaTeX
        self.context_buffer.append(char)
        if len(self.context_buffer) > self.max_context * 2:
            self.context_buffer.pop(0)

        return False

    def latex_completed(self, char_index: int, expression: str) -> None:
        """Called when a LaTeX expression is completed"""
        if self.enabled:
            self.latex_end_char = char_index
            self.log(f"--- LATEX EXPRESSION COMPLETED (char {char_index}) ---")
            self.log(f"Complete expression: '{expression}'")
            self.log(f"Expression length: {len(expression)}")
            # Will continue logging for a few more characters for context

    def latex_context_end(self, char_index: int) -> None:
        """Called when we're done logging LaTeX context"""
        if self.enabled:
            self.log(f"--- LATEX CONTEXT END (char {char_index}) ---\n")
            self.in_latex_context = False

    def close(self) -> None:
        """Close the log file"""
        if self.enabled and self.log_file:
            self.log("=== LaTeX Streaming Debug Session Ended ===")
            self.log_file.close()
            self.log_file = None


class StreamingMode(Enum):
    CHARACTER = "character"
    WORD = "word"
    INSTANT = "instant"


class LaTeXBuffer:
    """
    Smart buffer for LaTeX mathematical expressions during streaming.
    Prevents partial LaTeX from being rendered during character-by-character streaming.
    """

    def __init__(self, logger: Optional[LaTeXDebugLogger] = None):
        self.buffer = ""
        self.in_block_math = False
        self.in_inline_math = False
        self.block_math_pattern = re.compile(r"\$\$.*?\$\$", re.DOTALL)
        self.inline_math_pattern = re.compile(r"\$[^$]+\$")
        self.logger = logger
        self.char_count = 0  # Track character position for logging

    def add_character(self, char: str) -> tuple[str, bool]:
        """
        Add a character to the buffer and return (text_to_display, should_display)

        Returns:
            tuple: (text_to_display, should_display_now)
        """
        self.char_count += 1
        if self.logger is not None:
            should_log = self.logger.should_log_char(char, self.char_count)

        if should_log:
            if self.logger is not None:
                self.logger.log(
                    f"CHAR #{self.char_count}: '{char}' -> Buffer: '{self.buffer + char}'"
                )
                self.logger.log(
                    f"  State: block_math={self.in_block_math}, inline_math={self.in_inline_math}"
                )

        self.buffer += char

        # Check for block math delimiters
        if char == "$":
            if self.buffer.endswith("$$"):
                if not self.in_block_math:
                    # Starting block math - reset inline math flag if it was set by first $
                    self.in_block_math = True
                    self.in_inline_math = False  # Reset inline math flag
                    if should_log:
                        if self.logger is not None:
                            self.logger.log(
                                f"  -> BLOCK MATH START: Buffer now '{self.buffer}' (inline_math reset to False)"
                            )
                    return "", False  # Don't display yet
                else:
                    # Ending block math - ensure both flags are reset
                    self.in_block_math = False
                    self.in_inline_math = False  # Critical: reset inline math flag
                    result = self.buffer
                    self.buffer = ""
                    if self.logger is not None:
                        self.logger.latex_completed(self.char_count, result)
                    if should_log:
                        if self.logger is not None:
                            self.logger.log(
                                f"  -> BLOCK MATH END: Returning '{result}' (len={len(result)}) - BOTH FLAGS RESET"
                            )
                    return result, True
            elif not self.in_block_math:
                if not self.in_inline_math:
                    # Starting inline math
                    self.in_inline_math = True
                    if should_log:
                        if self.logger is not None:
                            self.logger.log(
                                f"  -> INLINE MATH START: Buffer now '{self.buffer}'"
                            )
                    return "", False  # Don't display yet
                else:
                    # Ending inline math
                    self.in_inline_math = False
                    result = self.buffer
                    self.buffer = ""
                    if self.logger is not None:
                        self.logger.latex_completed(self.char_count, result)
                    if should_log:
                        if self.logger is not None:
                            self.logger.log(
                                f"  -> INLINE MATH END: Returning '{result}' (len={len(result)})"
                            )
                    return result, True

        # If we're inside math, buffer everything
        if self.in_block_math or self.in_inline_math:
            if should_log:
                if self.logger is not None:
                    self.logger.log(
                        f"  -> BUFFERING (in math): '{char}' added to buffer"
                    )
            return "", False

        # Not in math, return the character immediately
        result = self.buffer
        self.buffer = ""
        if should_log:
            if self.logger is not None:
                self.logger.log(f"  -> IMMEDIATE DISPLAY: '{result}'")
            # Check if we should end context logging
            if self.logger is not None:
                if (
                    hasattr(self.logger, "latex_end_char")
                    and self.char_count
                    > self.logger.latex_end_char + self.logger.max_context
                ):
                    self.logger.latex_context_end(self.char_count)
        return result, True

    def add_text(self, text: str) -> str:
        """
        Add text and return what should be displayed immediately.
        For word-by-word streaming, we process complete words.
        """
        self.buffer += text

        # Check if we have complete math expressions
        display_text = ""
        remaining_text = self.buffer

        # Process block math first
        while True:
            match = self.block_math_pattern.search(remaining_text)
            if not match:
                break

            # Add text before the math
            display_text += remaining_text[: match.start()]
            # Add the complete math expression
            display_text += match.group()
            # Continue with remaining text
            remaining_text = remaining_text[match.end() :]

        # Process inline math
        while True:
            match = self.inline_math_pattern.search(remaining_text)
            if not match:
                break

            # Add text before the math
            display_text += remaining_text[: match.start()]
            # Add the complete math expression
            display_text += match.group()
            # Continue with remaining text
            remaining_text = remaining_text[match.end() :]

        # Check if remaining text contains partial math
        has_partial_block = (
            "$$" in remaining_text and remaining_text.count("$$") % 2 == 1
        )
        has_partial_inline = (
            "$" in remaining_text
            and not has_partial_block
            and remaining_text.count("$") % 2 == 1
        )

        if has_partial_block or has_partial_inline:
            # Keep partial math in buffer
            self.buffer = remaining_text
        else:
            # No partial math, display everything
            display_text += remaining_text
            self.buffer = ""

        return display_text

    def flush(self) -> str:
        """Return any remaining buffered content"""
        result = self.buffer
        self.buffer = ""
        return result


@dataclass
class StreamingConfig:
    """Configuration for streaming behavior"""

    mode: StreamingMode
    delay: float  # Delay between characters/words in seconds
    queue_size: int = 100  # Maximum queue size
    polling_interval: float = 0.01  # How often to check queue in main thread
    producer_timeout: float = 30.0  # How long to wait for producer to finish
    queue_timeout: float = 5.0  # Timeout for individual queue operations


class StreamlitStreamingManager:
    """
    Streamlit-specific wrapper for StreamingQueue that handles UI state management.

    This class provides a simpler approach that works better with Streamlit's execution model.
    """

    def __init__(self) -> None:
        self.config: Optional[StreamingConfig] = None

    def process_streamed_response(
        self,
        stream_source: Iterator[Dict[str, Any]],
        message_placeholder: DeltaGenerator,
        quill_icon: str | None,
        streaming_mode: str,
        streaming_delay: float,
        debug: bool = True,
    ) -> Dict[str, Any]:
        """
        Process streaming response with queue-based shock absorber pattern.

        This method implements the producer-consumer pattern in a Streamlit-friendly way.
        """
        # Create smart logger for LaTeX debugging
        latex_logger = LaTeXDebugLogger(enabled=debug)

        # Create configuration
        mode_map = {
            "character": StreamingMode.CHARACTER,
            "word": StreamingMode.WORD,
            "instant": StreamingMode.INSTANT,
        }
        mode = mode_map.get(streaming_mode, StreamingMode.CHARACTER)
        self.config = StreamingConfig(mode=mode, delay=streaming_delay)

        # Use queue for shock absorber pattern
        chunk_queue: queue.Queue = queue.Queue(maxsize=10000)
        producer_finished = threading.Event()
        producer_error: list[Union[Optional[Exception], None]] = [
            None
        ]  # Use list for mutable reference
        completion_metadata: list[Union[Dict[str, Any], None]] = [None]

        def producer_worker() -> None:
            """Producer thread that feeds the queue"""
            try:
                chunk_count = 0
                for chunk_data in stream_source:
                    chunk_count += 1
                    # Only log chunks that contain LaTeX-like content
                    if debug and chunk_data.get("answer_chunk"):
                        chunk_text = chunk_data["answer_chunk"]
                        if "$" in chunk_text:
                            latex_logger.log(
                                f"\n=== CHUNK #{chunk_count} (contains LaTeX) ==="
                            )
                            latex_logger.log(f"Chunk content: '{chunk_text}'")
                            latex_logger.log(f"Chunk length: {len(chunk_text)}")

                    if chunk_data.get("answer_chunk"):
                        try:
                            if self.config is not None:
                                chunk_queue.put(
                                    chunk_data, timeout=self.config.queue_timeout
                                )
                        except queue.Full:
                            print("Warning: Queue full, dropping chunk")
                            continue

                    # Handle safety violations and errors immediately
                    elif (
                        chunk_data.get("is_injection_attempt")
                        or chunk_data.get("is_off_topic")
                        or chunk_data.get("error")
                    ):
                        completion_metadata[0] = chunk_data
                        break

                    if chunk_data.get("is_complete"):
                        completion_metadata[0] = chunk_data
                        break

                if debug:
                    latex_logger.log(
                        f"\n=== PRODUCER FINISHED - Total chunks: {chunk_count} ==="
                    )

            except Exception as e:
                producer_error[0] = e
                print(f"Producer error: {e}")
            finally:
                producer_finished.set()

        # Start producer thread
        producer_thread = threading.Thread(target=producer_worker, daemon=True)
        producer_thread.start()

        # Consumer logic (runs in main thread)
        accumulated_text = ""
        display_text = ""
        latex_buffer = LaTeXBuffer(logger=latex_logger)
        start_time = time.time()
        max_total_time = 300.0  # 5 minutes maximum total time

        try:
            while not producer_finished.is_set() or not chunk_queue.empty():
                # Check for overall timeout
                if time.time() - start_time > max_total_time:
                    producer_error[0] = Exception(
                        "Total processing time exceeded 5 minutes"
                    )
                    break

                try:
                    # Get chunk with timeout
                    chunk_data = chunk_queue.get(
                        timeout=0.5
                    )  # Increased from 0.1 to 0.5

                    if chunk_data.get("answer_chunk"):
                        chunk_text = chunk_data["answer_chunk"]
                        accumulated_text += chunk_text

                        # Only log chunks that might contain LaTeX
                        if debug and "$" in chunk_text:
                            latex_logger.log(
                                f"\n--- CONSUMER PROCESSING LATEX CHUNK ---"
                            )
                            latex_logger.log(f"Chunk text: '{chunk_text}'")
                            latex_logger.log(f"Processing mode: {mode}")

                        if mode == StreamingMode.INSTANT:
                            # Instant mode - update immediately
                            display_text = accumulated_text
                            message_placeholder.markdown(
                                display_text
                                + f"<img src='data:image/png;base64,{quill_icon}' style='width: 40px; height: 40px; display: inline; vertical-align: bottom; transform: translateY(-5px);'>",
                                unsafe_allow_html=True,
                            )
                        elif mode == StreamingMode.CHARACTER:
                            # Character mode - animate each character with LaTeX awareness
                            for i, char in enumerate(chunk_text):
                                (
                                    char_to_display,
                                    should_display,
                                ) = latex_buffer.add_character(char)

                                if should_display and char_to_display:
                                    display_text += char_to_display

                                    # Log timing information for LaTeX expressions
                                    if (
                                        debug and len(char_to_display) > 1
                                    ):  # Likely a LaTeX expression
                                        latex_logger.log(
                                            f"DISPLAY UPDATE: '{char_to_display}' -> UI updated"
                                        )
                                        latex_logger.log(
                                            f"Display delay: {streaming_delay}s"
                                        )

                                    message_placeholder.markdown(
                                        display_text
                                        + f"<img src='data:image/png;base64,{quill_icon}' style='width: 40px; height: 40px; display: inline; vertical-align: bottom; transform: translateY(-5px);'>",
                                        unsafe_allow_html=True,
                                    )
                                    if streaming_delay > 0:
                                        time.sleep(streaming_delay)
                                else:
                                    # Even when buffering, add a small delay to maintain rhythm
                                    # This prevents the system from racing through LaTeX content
                                    if streaming_delay > 0:
                                        time.sleep(streaming_delay)
                        elif mode == StreamingMode.WORD:
                            # Word mode - animate each word with LaTeX awareness
                            words_to_display = latex_buffer.add_text(chunk_text)
                            if words_to_display:
                                words = words_to_display.split()
                                for i, word in enumerate(words):
                                    if display_text and not display_text.endswith(" "):
                                        display_text += " " + word
                                    else:
                                        display_text += word

                                    message_placeholder.markdown(
                                        display_text
                                        + f"<img src='data:image/png;base64,{quill_icon}' style='width: 40px; height: 40px; display: inline; vertical-align: bottom; transform: translateY(-5px);'>",
                                        unsafe_allow_html=True,
                                    )
                                    if i < len(words) - 1 and streaming_delay > 0:
                                        time.sleep(streaming_delay)

                except queue.Empty:
                    continue
                except Exception as e:
                    producer_error[0] = e
                    break

            # Flush any remaining LaTeX content
            remaining_latex = latex_buffer.flush()
            if remaining_latex:
                display_text += remaining_latex

            # Wait for producer to finish
            producer_thread.join(timeout=2.0)

            # Close the logger
            latex_logger.close()

            # Check for errors
            if producer_error[0]:
                return {
                    "error": str(producer_error[0]),
                    "final_text": accumulated_text,
                    "answer": accumulated_text,
                }

            # Return success result
            result = completion_metadata[0] if completion_metadata[0] else {}
            result.update({"final_text": accumulated_text, "answer": accumulated_text})
            return result

        except Exception as e:
            # Make sure to close logger even if there's an error
            latex_logger.close()
            return {
                "error": str(e),
                "final_text": accumulated_text,
                "answer": accumulated_text,
            }


# Utility functions for easy integration


def create_streaming_config(
    streaming_mode: str, streaming_delay: float
) -> StreamingConfig:
    """Create StreamingConfig from chat interface parameters"""
    mode_map = {
        "character": StreamingMode.CHARACTER,
        "word": StreamingMode.WORD,
        "instant": StreamingMode.INSTANT,
    }

    mode = mode_map.get(streaming_mode, StreamingMode.CHARACTER)
    return StreamingConfig(mode=mode, delay=streaming_delay)


def handle_streamed_response(
    stream_source: Iterator[Dict[str, Any]],
    message_placeholder: DeltaGenerator,
    quill_icon: str | None,
    streaming_mode: str,
    streaming_delay: float,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    High-level function to handle streaming with the new queue system.

    This is the main integration point for the chat interface.
    """
    manager = StreamlitStreamingManager()
    return manager.process_streamed_response(
        stream_source=stream_source,
        message_placeholder=message_placeholder,
        quill_icon=quill_icon,
        streaming_mode=streaming_mode,
        streaming_delay=streaming_delay,
        debug=debug,
    )

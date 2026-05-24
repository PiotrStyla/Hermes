"""Thin wrapper over the Twilio REST SDK with a `dry_run` mode.

In `dry_run=True` mode (default when credentials are missing) we never call
the network — the wrapper just prints the payload that *would* have been
sent. This lets the rest of the system be exercised end-to-end without an
account / public webhook URL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rich.console import Console

from .config import TelephonyConfig


@dataclass
class CallInitResult:
    call_sid: str
    dry_run: bool
    raw: dict[str, Any] | None = None


class TwilioCallClient:
    """Initiate outbound calls and clean up recordings."""

    def __init__(
        self,
        config: TelephonyConfig | None = None,
        dry_run: bool | None = None,
        console: Console | None = None,
    ):
        self.config = config or TelephonyConfig.from_env()
        self.console = console or Console()
        # Auto-enable dry-run if credentials are missing, unless explicitly overridden.
        if dry_run is None:
            dry_run = not self.config.is_configured() or not self.config.public_base_url
        self.dry_run = dry_run

    # ---- Outbound dial ----

    def initiate_call(
        self,
        to_number: str,
        call_id_param: str,
    ) -> CallInitResult:
        """Place an outbound call.

        On success Twilio assigns a real `CallSid`. In dry-run we synthesize
        a fake one so the rest of the pipeline (state files, webhooks tested
        manually) still works.
        """
        cfg = self.config
        url = f"{cfg.public_base_url}/twilio/start?call_id={call_id_param}"
        status_url = f"{cfg.public_base_url}/twilio/status?call_id={call_id_param}"

        payload = {
            "to": to_number,
            "from_": cfg.from_number,
            "url": url,
            "method": "POST",
            "status_callback": status_url,
            "status_callback_event": ["initiated", "ringing", "answered", "completed"],
            "status_callback_method": "POST",
            "machine_detection": cfg.machine_detection or None,
            "record": False,  # We capture audio per-turn via <Record> in TwiML, not full call.
        }

        if self.dry_run:
            self.console.print(
                "[yellow]⚠ Twilio dry-run: would have placed call with payload:[/yellow]"
            )
            for k, v in payload.items():
                # Mask phone number tail so screenshots don't leak it.
                if k == "to" and isinstance(v, str) and len(v) > 6:
                    v = v[:4] + "***" + v[-2:]
                self.console.print(f"  {k}: {v}")
            return CallInitResult(call_sid=f"DRY-{call_id_param}", dry_run=True)

        # Real call — lazy import the SDK.
        from twilio.rest import Client

        client = Client(cfg.account_sid, cfg.auth_token)
        call = client.calls.create(**{k: v for k, v in payload.items() if v is not None})
        return CallInitResult(call_sid=call.sid, dry_run=False, raw={"sid": call.sid})

    # ---- Cleanup ----

    def delete_recording(self, recording_sid: str) -> bool:
        """Delete a Twilio-side recording (RODO data minimization).

        Returns True on success or in dry-run; False if the SDK call fails.
        """
        if self.dry_run:
            self.console.print(
                f"[yellow]⚠ Twilio dry-run: would DELETE recording {recording_sid}[/yellow]"
            )
            return True
        try:
            from twilio.rest import Client

            client = Client(self.config.account_sid, self.config.auth_token)
            client.recordings(recording_sid).delete()
            return True
        except Exception as exc:  # noqa: BLE001
            self.console.print(f"[red]Failed to delete recording {recording_sid}: {exc}[/red]")
            return False

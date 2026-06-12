"""Zustandsmaschine der Gestensteuerung.

Bewusst ohne OpenCV-/MediaPipe-Abhaengigkeit gehalten: Die Maschine bekommt
pro Frame nur Zeitstempel und Pinch-Eingaben und liefert Zustand, Rechteck
und Ereignisse zurueck. Dadurch ist sie ohne Kamera testbar.

Zustaende und Uebergaenge:

    IDLE      --(beide Haende pinchen, stabil >= PINCH_STABIL_S)-->   FRAMING
    FRAMING   --(beide Pinches offen, stabil >= OEFFNEN_STABIL_S)-->  COUNTDOWN
    FRAMING   --(Haende/Tracking verloren > TRACKING_VERLUST_S)-->    IDLE
    COUNTDOWN --(COUNTDOWN_DAUER_S abgelaufen)--> CAPTURE --(sofort)--> IDLE

Alle Entprellungen laufen ueber Zeitstempel, nicht ueber Frame-Zaehler.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto

import config

Rechteck = tuple[int, int, int, int]
"""Achsenparalleles Rechteck als (x1, y1, x2, y2) mit x1 < x2 und y1 < y2."""


class Zustand(Enum):
    """Die vier Zustaende der Gestensteuerung."""

    IDLE = auto()
    FRAMING = auto()
    COUNTDOWN = auto()
    CAPTURE = auto()


@dataclass(frozen=True)
class PinchEingabe:
    """Gesten-Information einer einzelnen erkannten Hand."""

    pinch_aktiv: bool
    punkt: tuple[int, int]


@dataclass(frozen=True)
class StatusErgebnis:
    """Ergebnis eines Update-Schritts der Zustandsmaschine."""

    zustand: Zustand
    rechteck: Rechteck | None
    countdown_rest: int | None
    tick: bool
    ausloesen: Rechteck | None


def baue_rechteck(
    punkt_a: tuple[int, int],
    punkt_b: tuple[int, int],
    frame_breite: int,
    frame_hoehe: int,
) -> Rechteck:
    """Bildet aus zwei Pinch-Punkten ein sortiertes, geclamptes Rechteck."""
    x1, x2 = sorted((punkt_a[0], punkt_b[0]))
    y1, y2 = sorted((punkt_a[1], punkt_b[1]))
    x1 = max(0, min(x1, frame_breite - 1))
    x2 = max(0, min(x2, frame_breite - 1))
    y1 = max(0, min(y1, frame_hoehe - 1))
    y2 = max(0, min(y2, frame_hoehe - 1))
    return (x1, y1, x2, y2)


def rechteck_gross_genug(rechteck: Rechteck) -> bool:
    """Prueft, ob das Rechteck die konfigurierte Mindestgroesse erreicht."""
    x1, y1, x2, y2 = rechteck
    return (x2 - x1) >= config.MIN_RECHTECK_PX and (y2 - y1) >= config.MIN_RECHTECK_PX


class GestenStateMachine:
    """Verwaltet die Zustaende IDLE, FRAMING, COUNTDOWN und CAPTURE."""

    def __init__(self, frame_breite: int, frame_hoehe: int) -> None:
        self._frame_breite = frame_breite
        self._frame_hoehe = frame_hoehe
        self._zustand: Zustand = Zustand.IDLE
        self._beide_pinch_seit: float | None = None
        self._offen_seit: float | None = None
        self._verloren_seit: float | None = None
        self._rechteck: Rechteck | None = None
        self._countdown_start: float | None = None
        self._letzte_countdown_sekunde: int | None = None

    @property
    def zustand(self) -> Zustand:
        """Aktueller Zustand der Maschine."""
        return self._zustand

    def update(self, jetzt: float, haende: list[PinchEingabe]) -> StatusErgebnis:
        """Verarbeitet einen Frame: Zeitstempel + Gesten rein, Status raus."""
        pinch_punkte = [hand.punkt for hand in haende if hand.pinch_aktiv]
        beide_pinchen = len(haende) >= 2 and len(pinch_punkte) >= 2
        beide_offen = len(haende) >= 2 and len(pinch_punkte) == 0
        haende_verloren = len(haende) < 2

        if self._zustand is Zustand.IDLE:
            self._update_idle(jetzt, beide_pinchen, pinch_punkte)
        elif self._zustand is Zustand.FRAMING:
            self._update_framing(
                jetzt, beide_pinchen, beide_offen, haende_verloren, pinch_punkte
            )

        if self._zustand is Zustand.COUNTDOWN:
            return self._update_countdown(jetzt)

        return StatusErgebnis(
            zustand=self._zustand,
            rechteck=self._rechteck if self._zustand is Zustand.FRAMING else None,
            countdown_rest=None,
            tick=False,
            ausloesen=None,
        )

    # ------------------------------------------------------------------ intern

    def _update_idle(
        self,
        jetzt: float,
        beide_pinchen: bool,
        pinch_punkte: list[tuple[int, int]],
    ) -> None:
        """IDLE: wartet auf stabilen Doppel-Pinch."""
        if not beide_pinchen:
            self._beide_pinch_seit = None
            return
        if self._beide_pinch_seit is None:
            self._beide_pinch_seit = jetzt
        if jetzt - self._beide_pinch_seit >= config.PINCH_STABIL_S:
            self._zustand = Zustand.FRAMING
            self._rechteck = baue_rechteck(
                pinch_punkte[0], pinch_punkte[1], self._frame_breite, self._frame_hoehe
            )
            self._offen_seit = None
            self._verloren_seit = None

    def _update_framing(
        self,
        jetzt: float,
        beide_pinchen: bool,
        beide_offen: bool,
        haende_verloren: bool,
        pinch_punkte: list[tuple[int, int]],
    ) -> None:
        """FRAMING: Rechteck folgt den Pinch-Punkten, Loslassen startet Countdown."""
        if haende_verloren:
            if self._verloren_seit is None:
                self._verloren_seit = jetzt
            if jetzt - self._verloren_seit > config.TRACKING_VERLUST_S:
                self._zuruecksetzen()
            return
        self._verloren_seit = None

        if beide_pinchen:
            self._rechteck = baue_rechteck(
                pinch_punkte[0], pinch_punkte[1], self._frame_breite, self._frame_hoehe
            )
            self._offen_seit = None
            return

        if not beide_offen:
            # Mischzustand (eine Hand pincht noch): Rechteck einfrieren, warten.
            self._offen_seit = None
            return

        if self._offen_seit is None:
            self._offen_seit = jetzt
        if jetzt - self._offen_seit >= config.OEFFNEN_STABIL_S:
            if self._rechteck is not None and rechteck_gross_genug(self._rechteck):
                self._zustand = Zustand.COUNTDOWN
                self._countdown_start = jetzt
                self._letzte_countdown_sekunde = None
            else:
                self._zuruecksetzen()

    def _update_countdown(self, jetzt: float) -> StatusErgebnis:
        """COUNTDOWN: zaehlt sichtbar herunter und loest danach CAPTURE aus."""
        assert self._countdown_start is not None
        rest = config.COUNTDOWN_DAUER_S - (jetzt - self._countdown_start)

        if rest <= 0:
            rechteck = self._rechteck
            self._zuruecksetzen()
            return StatusErgebnis(
                zustand=Zustand.CAPTURE,
                rechteck=rechteck,
                countdown_rest=None,
                tick=False,
                ausloesen=rechteck,
            )

        sekunde = math.ceil(rest)
        tick = sekunde != self._letzte_countdown_sekunde
        self._letzte_countdown_sekunde = sekunde
        return StatusErgebnis(
            zustand=Zustand.COUNTDOWN,
            rechteck=self._rechteck,
            countdown_rest=sekunde,
            tick=tick,
            ausloesen=None,
        )

    def _zuruecksetzen(self) -> None:
        """Setzt die Maschine vollstaendig auf IDLE zurueck."""
        self._zustand = Zustand.IDLE
        self._beide_pinch_seit = None
        self._offen_seit = None
        self._verloren_seit = None
        self._rechteck = None
        self._countdown_start = None
        self._letzte_countdown_sekunde = None

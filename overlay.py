"""Alles Zeichnen im OpenCV-Fenster.

Rechteck, Countdown, Statustext, Hand-Landmarks, Pinch-Punkte sowie die
beiden zeitgesteuerten Effekte Blitz und Foto-Vorschau.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

import config
from hand_tracker import DAUMENSPITZE, ZEIGEFINGERSPITZE, HandDaten
from state_machine import Rechteck

# Landmark-Paare des MediaPipe-Hand-Skeletts (HAND_CONNECTIONS).
HAND_VERBINDUNGEN: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),          # Daumen
    (0, 5), (5, 6), (6, 7), (7, 8),          # Zeigefinger
    (5, 9), (9, 10), (10, 11), (11, 12),     # Mittelfinger
    (9, 13), (13, 14), (14, 15), (15, 16),   # Ringfinger
    (13, 17), (17, 18), (18, 19), (19, 20),  # kleiner Finger
    (0, 17),                                 # Handflaeche
)


def zeichne_landmarks(frame: np.ndarray, haende: list[HandDaten]) -> None:
    """Zeichnet das Hand-Skelett: dezente Linien, Punkte, markante Spitzen."""
    for hand in haende:
        punkte = hand.landmark_punkte
        for start, ende in HAND_VERBINDUNGEN:
            cv2.line(
                frame,
                punkte[start],
                punkte[ende],
                config.FARBE_LANDMARK_LINIE,
                config.LANDMARK_LINIENSTAERKE,
                cv2.LINE_AA,
            )
        for punkt in punkte:
            cv2.circle(frame, punkt, config.LANDMARK_RADIUS, config.FARBE_LANDMARK, -1)
        # Daumen- und Zeigefingerspitze hervorheben - sie steuern den Pinch.
        for spitze in (DAUMENSPITZE, ZEIGEFINGERSPITZE):
            cv2.circle(
                frame,
                punkte[spitze],
                config.FINGERSPITZEN_RADIUS,
                config.FARBE_FINGERSPITZE,
                -1,
            )


def zeichne_pinch_punkte(frame: np.ndarray, haende: list[HandDaten]) -> None:
    """Markiert aktive Pinch-Punkte mit auffaelligen Kreisen."""
    for hand in haende:
        if hand.pinch_aktiv:
            cv2.circle(
                frame,
                hand.pinch_punkt,
                config.PINCH_PUNKT_RADIUS,
                config.FARBE_PINCH_PUNKT,
                2,
            )


def zeichne_rechteck(frame: np.ndarray, rechteck: Rechteck) -> None:
    """Zeichnet das aufgespannte Auswahl-Rechteck."""
    x1, y1, x2, y2 = rechteck
    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        config.FARBE_RECHTECK,
        config.RECHTECK_LINIENSTAERKE,
    )


def zeichne_status(frame: np.ndarray, text: str) -> None:
    """Schreibt den Statustext mit Schatten oben links ins Bild."""
    position = (16, 32)
    schatten = (position[0] + 2, position[1] + 2)
    for farbe, ort in (
        (config.FARBE_STATUS_SCHATTEN, schatten),
        (config.FARBE_STATUS_TEXT, position),
    ):
        cv2.putText(
            frame,
            text,
            ort,
            cv2.FONT_HERSHEY_SIMPLEX,
            config.STATUS_SCHRIFT_GROESSE,
            farbe,
            2,
            cv2.LINE_AA,
        )


def zeichne_countdown(frame: np.ndarray, sekunden: int) -> None:
    """Rendert die verbleibenden Countdown-Sekunden gross und zentriert."""
    text = str(sekunden)
    (text_breite, text_hoehe), _ = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        config.COUNTDOWN_SCHRIFT_GROESSE,
        config.COUNTDOWN_LINIENSTAERKE,
    )
    hoehe, breite = frame.shape[:2]
    position = ((breite - text_breite) // 2, (hoehe + text_hoehe) // 2)
    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        config.COUNTDOWN_SCHRIFT_GROESSE,
        config.FARBE_COUNTDOWN,
        config.COUNTDOWN_LINIENSTAERKE,
        cv2.LINE_AA,
    )


class BlitzEffekt:
    """Weisses Overlay mit abnehmender Deckkraft fuer einige Frames."""

    def __init__(self) -> None:
        self._verbleibende_frames = 0

    def ausloesen(self) -> None:
        """Startet den Blitz beim naechsten gezeichneten Frame."""
        self._verbleibende_frames = config.BLITZ_FRAMES

    def anwenden(self, frame: np.ndarray) -> None:
        """Blendet das weisse Overlay ein, solange der Blitz aktiv ist."""
        if self._verbleibende_frames <= 0:
            return
        deckkraft = config.BLITZ_START_DECKKRAFT * (
            self._verbleibende_frames / config.BLITZ_FRAMES
        )
        weiss = np.full_like(frame, 255)
        cv2.addWeighted(weiss, deckkraft, frame, 1.0 - deckkraft, 0, dst=frame)
        self._verbleibende_frames -= 1


class FotoVorschau:
    """Zeigt das zuletzt geschossene Foto kurz als Thumbnail oben rechts.

    Das Thumbnail ist klickbar: Ueber `pfad_bei_klick` laesst sich pruefen,
    ob ein Mausklick das Thumbnail getroffen hat, um das Foto zu oeffnen.
    """

    def __init__(self) -> None:
        self._bild: np.ndarray | None = None
        self._anzeige_bis: float = 0.0
        self._foto_pfad: Path | None = None
        self._bereich: tuple[int, int, int, int] | None = None  # x1, y1, x2, y2

    def zeigen(self, bild: np.ndarray, jetzt: float, foto_pfad: Path | None) -> None:
        """Merkt sich Foto + Speicherpfad und startet die Anzeigezeit."""
        self._bild = bild.copy()
        self._foto_pfad = foto_pfad
        self._anzeige_bis = jetzt + config.VORSCHAU_DAUER_S

    def pfad_bei_klick(self, x: int, y: int) -> Path | None:
        """Gibt den Foto-Pfad zurueck, wenn (x, y) das sichtbare Thumbnail trifft."""
        if self._bereich is None or self._foto_pfad is None:
            return None
        x1, y1, x2, y2 = self._bereich
        if x1 <= x <= x2 and y1 <= y <= y2:
            return self._foto_pfad
        return None

    def anwenden(self, frame: np.ndarray, jetzt: float) -> None:
        """Blendet das Thumbnail ein, solange die Anzeigezeit laeuft."""
        if self._bild is None or jetzt >= self._anzeige_bis:
            self._bild = None
            self._bereich = None
            return

        frame_hoehe, frame_breite = frame.shape[:2]
        max_breite = int(frame_breite * config.VORSCHAU_MAX_BREITE_ANTEIL)
        bild_hoehe, bild_breite = self._bild.shape[:2]
        faktor = max_breite / bild_breite
        thumb_breite = max(1, int(bild_breite * faktor))
        thumb_hoehe = max(1, int(bild_hoehe * faktor))
        thumbnail = cv2.resize(self._bild, (thumb_breite, thumb_hoehe))

        rand = config.VORSCHAU_RAND_PX
        x1 = frame_breite - rand - thumb_breite
        y1 = rand
        if x1 < 0 or y1 + thumb_hoehe > frame_hoehe:
            self._bereich = None
            return

        frame[y1 : y1 + thumb_hoehe, x1 : x1 + thumb_breite] = thumbnail
        cv2.rectangle(
            frame,
            (x1, y1),
            (x1 + thumb_breite, y1 + thumb_hoehe),
            config.FARBE_VORSCHAU_RAHMEN,
            config.VORSCHAU_RAHMEN_PX,
        )
        self._bereich = (x1, y1, x1 + thumb_breite, y1 + thumb_hoehe)

        if self._foto_pfad is not None:
            cv2.putText(
                frame,
                config.VORSCHAU_KLICK_HINWEIS,
                (x1, y1 + thumb_hoehe + 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                config.FARBE_VORSCHAU_RAHMEN,
                1,
                cv2.LINE_AA,
            )

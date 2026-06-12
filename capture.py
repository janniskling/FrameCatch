"""Foto-Ausschnitt speichern und Sounds abspielen.

Sounds laufen ueber das macOS-Bordmittel `afplay` (nicht-blockierend via
subprocess), es wird keine zusaetzliche Sound-Library benoetigt.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

import config
from state_machine import Rechteck


def speichere_ausschnitt(frame: np.ndarray, rechteck: Rechteck) -> Path | None:
    """Speichert den Rechteck-Ausschnitt als JPG und gibt den Pfad zurueck.

    Der Zielordner wird bei Bedarf angelegt. Liefert None, wenn der
    Ausschnitt leer ist oder das Speichern fehlschlaegt.
    """
    x1, y1, x2, y2 = rechteck
    ausschnitt = frame[y1:y2, x1:x2]
    if ausschnitt.size == 0:
        return None

    ordner = Path(config.FOTO_ORDNER)
    ordner.mkdir(parents=True, exist_ok=True)
    zeitstempel = datetime.now().strftime("%Y%m%d_%H%M%S")
    pfad = ordner / f"{config.FOTO_PREFIX}_{zeitstempel}.jpg"

    erfolgreich = cv2.imwrite(
        str(pfad), ausschnitt, [cv2.IMWRITE_JPEG_QUALITY, config.JPG_QUALITAET]
    )
    return pfad if erfolgreich else None


def spiele_sound(sound_pfad: str) -> None:
    """Spielt eine Sound-Datei nicht-blockierend ueber `afplay` ab."""
    try:
        subprocess.Popen(
            ["afplay", sound_pfad],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        # Sound ist reines Feedback - Fehler duerfen die App nicht stoppen.
        pass


def oeffne_foto(pfad: Path) -> None:
    """Oeffnet ein gespeichertes Foto nicht-blockierend in der macOS-Vorschau."""
    try:
        subprocess.Popen(
            ["open", str(pfad)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass

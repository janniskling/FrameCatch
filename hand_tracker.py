"""MediaPipe-Wrapper fuer das Hand-Tracking.

Liefert pro erkannter Hand den Pinch-Status (Daumen- und Zeigefingerspitze
zusammen), den Pinch-Punkt sowie alle Landmark-Pixelkoordinaten fuers Zeichnen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np

import config

HANDGELENK = 0
DAUMENSPITZE = 4
ZEIGEFINGERSPITZE = 8
MITTELFINGER_ANSATZ = 9


@dataclass(frozen=True)
class HandDaten:
    """Aufbereitete Tracking-Daten einer einzelnen Hand."""

    pinch_aktiv: bool
    pinch_punkt: tuple[int, int]
    landmark_punkte: list[tuple[int, int]]


class HandTracker:
    """Kapselt die MediaPipe-Hands-Solution hinter einer schmalen API."""

    def __init__(self) -> None:
        self._hands = mp.solutions.hands.Hands(
            max_num_hands=config.MAX_ANZAHL_HAENDE,
            min_detection_confidence=config.MIN_ERKENNUNGS_KONFIDENZ,
            min_tracking_confidence=config.MIN_TRACKING_KONFIDENZ,
        )

    def verarbeite(self, frame_bgr: np.ndarray) -> list[HandDaten]:
        """Erkennt Haende im (bereits gespiegelten) BGR-Frame.

        Gibt pro Hand Pinch-Status, Pinch-Punkt (Mittelpunkt zwischen Daumen-
        und Zeigefingerspitze) und alle Landmarks in Pixelkoordinaten zurueck.
        Die Pinch-Schwelle skaliert mit der Handgroesse im Bild, damit die
        Geste unabhaengig vom Abstand zur Kamera gleich reagiert.
        """
        hoehe, breite = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        ergebnis = self._hands.process(frame_rgb)

        haende: list[HandDaten] = []
        if not ergebnis.multi_hand_landmarks:
            return haende

        for hand_landmarks in ergebnis.multi_hand_landmarks:
            punkte = [
                (round(landmark.x * breite), round(landmark.y * hoehe))
                for landmark in hand_landmarks.landmark
            ]
            daumen = punkte[DAUMENSPITZE]
            zeigefinger = punkte[ZEIGEFINGERSPITZE]
            distanz = math.dist(daumen, zeigefinger)

            hand_groesse = math.dist(punkte[HANDGELENK], punkte[MITTELFINGER_ANSATZ])
            schwelle = max(
                config.PINCH_SCHWELLE_MIN_PX,
                config.PINCH_VERHAELTNIS * hand_groesse,
            )

            pinch_punkt = (
                (daumen[0] + zeigefinger[0]) // 2,
                (daumen[1] + zeigefinger[1]) // 2,
            )
            haende.append(
                HandDaten(
                    pinch_aktiv=distanz < schwelle,
                    pinch_punkt=pinch_punkt,
                    landmark_punkte=punkte,
                )
            )
        return haende

    def schliessen(self) -> None:
        """Gibt die MediaPipe-Ressourcen frei."""
        self._hands.close()

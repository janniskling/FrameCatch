"""Einstiegspunkt von FrameCatch.

Verbindet Kamera-Loop, Hand-Tracking, Zustandsmaschine, Overlay und Capture:
Beide Haende pinchen -> Rechteck aufziehen, Pinches oeffnen -> Countdown,
danach wird der Ausschnitt als Foto gespeichert. Beenden mit Taste `q`.
"""

from __future__ import annotations

import sys
import time

import cv2

import config
from capture import oeffne_foto, speichere_ausschnitt, spiele_sound
from hand_tracker import HandTracker
from overlay import (
    BlitzEffekt,
    FotoVorschau,
    zeichne_countdown,
    zeichne_landmarks,
    zeichne_pinch_punkte,
    zeichne_rechteck,
    zeichne_status,
)
from state_machine import GestenStateMachine, PinchEingabe, Zustand

STATUS_TEXTE: dict[Zustand, str] = {
    Zustand.IDLE: "Beide Haende: Daumen+Zeigefinger zusammen -> Rahmen aufziehen",
    Zustand.FRAMING: "Rahmen aufziehen - beide Pinches oeffnen startet den Countdown",
    Zustand.COUNTDOWN: "Laecheln! Foto kommt gleich...",
    Zustand.CAPTURE: "Foto gespeichert!",
}

KAMERA_FEHLERMELDUNG = (
    "Fehler: Die Webcam konnte nicht geoeffnet werden.\n"
    "Moegliche Ursachen:\n"
    "  - Eine andere App (z. B. Zoom/FaceTime) belegt die Kamera.\n"
    "  - macOS-Kameraberechtigung fehlt: Systemeinstellungen -> "
    "Datenschutz & Sicherheit -> Kamera -> Terminal/Python erlauben."
)


def main() -> int:
    """Startet die Kamera-Schleife; gibt einen Exit-Code zurueck."""
    kamera = cv2.VideoCapture(config.KAMERA_INDEX)
    if not kamera.isOpened():
        print(KAMERA_FEHLERMELDUNG, file=sys.stderr)
        return 1

    erfolgreich, frame = kamera.read()
    if not erfolgreich or frame is None:
        print(KAMERA_FEHLERMELDUNG, file=sys.stderr)
        kamera.release()
        return 1

    hoehe, breite = frame.shape[:2]
    tracker = HandTracker()
    zustandsmaschine = GestenStateMachine(frame_breite=breite, frame_hoehe=hoehe)
    blitz = BlitzEffekt()
    vorschau = FotoVorschau()

    def bei_mausklick(event: int, x: int, y: int, _flags: int, _param: object) -> None:
        """Klick auf das Vorschau-Thumbnail oeffnet das gespeicherte Foto."""
        if event == cv2.EVENT_LBUTTONDOWN:
            pfad = vorschau.pfad_bei_klick(x, y)
            if pfad is not None:
                oeffne_foto(pfad)

    cv2.namedWindow(config.FENSTER_NAME)
    cv2.setMouseCallback(config.FENSTER_NAME, bei_mausklick)

    try:
        while True:
            erfolgreich, frame = kamera.read()
            if not erfolgreich or frame is None:
                print("Warnung: Kein Kamerabild mehr - beende.", file=sys.stderr)
                break

            # Selfie-Ansicht: alle Koordinaten und das gespeicherte Foto
            # beziehen sich auf das gespiegelte Bild.
            frame = cv2.flip(frame, 1)
            jetzt = time.monotonic()

            haende = tracker.verarbeite(frame)
            eingaben = [
                PinchEingabe(pinch_aktiv=hand.pinch_aktiv, punkt=hand.pinch_punkt)
                for hand in haende
            ]
            ergebnis = zustandsmaschine.update(jetzt, eingaben)

            if ergebnis.tick:
                spiele_sound(config.TICK_SOUND)

            # Capture aus dem sauberen Frame, bevor Overlays gezeichnet werden.
            if ergebnis.ausloesen is not None:
                pfad = speichere_ausschnitt(frame, ergebnis.ausloesen)
                if pfad is not None:
                    print(f"Foto gespeichert: {pfad}")
                    spiele_sound(config.AUSLOESE_SOUND)
                    blitz.ausloesen()
                    x1, y1, x2, y2 = ergebnis.ausloesen
                    vorschau.zeigen(frame[y1:y2, x1:x2], jetzt, pfad)

            zeichne_landmarks(frame, haende)
            zeichne_pinch_punkte(frame, haende)
            if ergebnis.rechteck is not None:
                zeichne_rechteck(frame, ergebnis.rechteck)
            if ergebnis.countdown_rest is not None:
                zeichne_countdown(frame, ergebnis.countdown_rest)
            zeichne_status(frame, STATUS_TEXTE[ergebnis.zustand])
            blitz.anwenden(frame)
            vorschau.anwenden(frame, jetzt)

            cv2.imshow(config.FENSTER_NAME, frame)
            taste = cv2.waitKey(1) & 0xFF
            if taste == ord(config.TASTE_BEENDEN):
                break
    finally:
        tracker.schliessen()
        kamera.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())

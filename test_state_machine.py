"""Unit-Tests fuer die Gesten-Zustandsmaschine (laufen ohne Kamera/OpenCV)."""

from __future__ import annotations

import config
from state_machine import (
    GestenStateMachine,
    PinchEingabe,
    Zustand,
    baue_rechteck,
    rechteck_gross_genug,
)

BREITE = 1280
HOEHE = 720


def pinch(x: int, y: int) -> PinchEingabe:
    """Hand mit aktivem Pinch am Punkt (x, y)."""
    return PinchEingabe(pinch_aktiv=True, punkt=(x, y))


def offen(x: int = 0, y: int = 0) -> PinchEingabe:
    """Hand ohne Pinch."""
    return PinchEingabe(pinch_aktiv=False, punkt=(x, y))


def neue_maschine() -> GestenStateMachine:
    return GestenStateMachine(frame_breite=BREITE, frame_hoehe=HOEHE)


def bringe_in_framing(
    maschine: GestenStateMachine, start: float = 0.0
) -> float:
    """Hilfsfunktion: fuehrt die Maschine stabil nach FRAMING, gibt Zeit zurueck."""
    haende = [pinch(100, 100), pinch(500, 400)]
    maschine.update(start, haende)
    jetzt = start + config.PINCH_STABIL_S + 0.01
    ergebnis = maschine.update(jetzt, haende)
    assert ergebnis.zustand is Zustand.FRAMING
    return jetzt


# --------------------------------------------------------------- Rechteck-Helfer


def test_baue_rechteck_sortiert_koordinaten() -> None:
    assert baue_rechteck((500, 400), (100, 100), BREITE, HOEHE) == (100, 100, 500, 400)


def test_baue_rechteck_clampt_an_framegrenzen() -> None:
    rechteck = baue_rechteck((-50, -20), (5000, 9000), BREITE, HOEHE)
    assert rechteck == (0, 0, BREITE - 1, HOEHE - 1)


def test_rechteck_gross_genug() -> None:
    seite = config.MIN_RECHTECK_PX
    assert rechteck_gross_genug((0, 0, seite, seite))
    assert not rechteck_gross_genug((0, 0, seite - 1, seite))
    assert not rechteck_gross_genug((0, 0, seite, seite - 1))


# ------------------------------------------------------------------ IDLE -> FRAMING


def test_idle_bleibt_ohne_haende() -> None:
    maschine = neue_maschine()
    ergebnis = maschine.update(0.0, [])
    assert ergebnis.zustand is Zustand.IDLE
    assert ergebnis.rechteck is None


def test_idle_nach_framing_erst_nach_stabilzeit() -> None:
    maschine = neue_maschine()
    haende = [pinch(100, 100), pinch(500, 400)]
    assert maschine.update(0.0, haende).zustand is Zustand.IDLE
    assert (
        maschine.update(config.PINCH_STABIL_S - 0.05, haende).zustand is Zustand.IDLE
    )
    ergebnis = maschine.update(config.PINCH_STABIL_S + 0.01, haende)
    assert ergebnis.zustand is Zustand.FRAMING
    assert ergebnis.rechteck == (100, 100, 500, 400)


def test_kurzer_pinch_aussetzer_verhindert_framing() -> None:
    maschine = neue_maschine()
    haende = [pinch(100, 100), pinch(500, 400)]
    maschine.update(0.0, haende)
    # Aussetzer: nur eine Hand pincht -> Entprell-Timer startet neu.
    maschine.update(0.2, [pinch(100, 100), offen()])
    ergebnis = maschine.update(0.4, haende)
    assert ergebnis.zustand is Zustand.IDLE


def test_einhaendiger_pinch_startet_kein_framing() -> None:
    maschine = neue_maschine()
    haende = [pinch(100, 100)]
    maschine.update(0.0, haende)
    assert maschine.update(1.0, haende).zustand is Zustand.IDLE


# ---------------------------------------------------------------- FRAMING-Verhalten


def test_framing_rechteck_folgt_pinch_punkten() -> None:
    maschine = neue_maschine()
    jetzt = bringe_in_framing(maschine)
    ergebnis = maschine.update(jetzt + 0.1, [pinch(200, 150), pinch(800, 600)])
    assert ergebnis.zustand is Zustand.FRAMING
    assert ergebnis.rechteck == (200, 150, 800, 600)


def test_framing_zurueck_zu_idle_bei_tracking_verlust() -> None:
    maschine = neue_maschine()
    jetzt = bringe_in_framing(maschine)
    assert maschine.update(jetzt + 0.1, []).zustand is Zustand.FRAMING
    ergebnis = maschine.update(
        jetzt + 0.1 + config.TRACKING_VERLUST_S + 0.01, []
    )
    assert ergebnis.zustand is Zustand.IDLE


def test_framing_uebersteht_kurzen_tracking_aussetzer() -> None:
    maschine = neue_maschine()
    jetzt = bringe_in_framing(maschine)
    maschine.update(jetzt + 0.1, [])
    ergebnis = maschine.update(jetzt + 0.3, [pinch(100, 100), pinch(500, 400)])
    assert ergebnis.zustand is Zustand.FRAMING


# ------------------------------------------------------------ FRAMING -> COUNTDOWN


def test_oeffnen_startet_countdown_mit_eingefrorenem_rechteck() -> None:
    maschine = neue_maschine()
    jetzt = bringe_in_framing(maschine)
    beide_offen = [offen(), offen()]
    maschine.update(jetzt + 0.1, beide_offen)
    ergebnis = maschine.update(
        jetzt + 0.1 + config.OEFFNEN_STABIL_S + 0.01, beide_offen
    )
    assert ergebnis.zustand is Zustand.COUNTDOWN
    assert ergebnis.rechteck == (100, 100, 500, 400)
    assert ergebnis.countdown_rest == 3
    assert ergebnis.tick is True


def test_kurzes_oeffnen_startet_keinen_countdown() -> None:
    maschine = neue_maschine()
    jetzt = bringe_in_framing(maschine)
    maschine.update(jetzt + 0.1, [offen(), offen()])
    # Vor Ablauf der Stabilzeit wieder gepincht -> weiter FRAMING.
    ergebnis = maschine.update(jetzt + 0.2, [pinch(100, 100), pinch(500, 400)])
    assert ergebnis.zustand is Zustand.FRAMING
    ergebnis = maschine.update(
        jetzt + 0.2 + config.OEFFNEN_STABIL_S + 0.01,
        [pinch(100, 100), pinch(500, 400)],
    )
    assert ergebnis.zustand is Zustand.FRAMING


def test_zu_kleines_rechteck_geht_zurueck_zu_idle() -> None:
    maschine = neue_maschine()
    haende = [pinch(100, 100), pinch(150, 150)]  # 50x50 px < Mindestgroesse
    maschine.update(0.0, haende)
    jetzt = config.PINCH_STABIL_S + 0.01
    assert maschine.update(jetzt, haende).zustand is Zustand.FRAMING
    beide_offen = [offen(), offen()]
    maschine.update(jetzt + 0.1, beide_offen)
    ergebnis = maschine.update(
        jetzt + 0.1 + config.OEFFNEN_STABIL_S + 0.01, beide_offen
    )
    assert ergebnis.zustand is Zustand.IDLE
    assert ergebnis.ausloesen is None


def test_mischzustand_eine_hand_pincht_friert_rechteck_ein() -> None:
    maschine = neue_maschine()
    jetzt = bringe_in_framing(maschine)
    gemischt = [pinch(100, 100), offen()]
    maschine.update(jetzt + 0.1, gemischt)
    ergebnis = maschine.update(jetzt + 2.0, gemischt)
    assert ergebnis.zustand is Zustand.FRAMING
    assert ergebnis.rechteck == (100, 100, 500, 400)


# ------------------------------------------------------- COUNTDOWN -> CAPTURE -> IDLE


def bringe_in_countdown(maschine: GestenStateMachine) -> float:
    """Hilfsfunktion: fuehrt die Maschine nach COUNTDOWN, gibt Startzeit zurueck."""
    jetzt = bringe_in_framing(maschine)
    beide_offen = [offen(), offen()]
    maschine.update(jetzt + 0.1, beide_offen)
    start = jetzt + 0.1 + config.OEFFNEN_STABIL_S + 0.01
    ergebnis = maschine.update(start, beide_offen)
    assert ergebnis.zustand is Zustand.COUNTDOWN
    return start


def test_countdown_zaehlt_sekunden_mit_ticks() -> None:
    maschine = neue_maschine()
    start = bringe_in_countdown(maschine)

    ergebnis = maschine.update(start + 0.5, [])
    assert ergebnis.countdown_rest == 3
    assert ergebnis.tick is False  # gleiche Sekunde wie beim Start

    ergebnis = maschine.update(start + 1.1, [])
    assert ergebnis.countdown_rest == 2
    assert ergebnis.tick is True

    ergebnis = maschine.update(start + 2.1, [])
    assert ergebnis.countdown_rest == 1
    assert ergebnis.tick is True


def test_countdown_loest_capture_aus_und_geht_zu_idle() -> None:
    maschine = neue_maschine()
    start = bringe_in_countdown(maschine)
    ergebnis = maschine.update(start + config.COUNTDOWN_DAUER_S + 0.01, [])
    assert ergebnis.zustand is Zustand.CAPTURE
    assert ergebnis.ausloesen == (100, 100, 500, 400)
    # Direkt danach ist die Maschine wieder in IDLE.
    assert maschine.zustand is Zustand.IDLE
    folge = maschine.update(start + config.COUNTDOWN_DAUER_S + 0.1, [])
    assert folge.zustand is Zustand.IDLE
    assert folge.ausloesen is None


def test_countdown_laeuft_auch_ohne_haende_weiter() -> None:
    maschine = neue_maschine()
    start = bringe_in_countdown(maschine)
    ergebnis = maschine.update(start + 1.5, [pinch(10, 10), pinch(20, 20)])
    assert ergebnis.zustand is Zustand.COUNTDOWN
    ergebnis = maschine.update(start + config.COUNTDOWN_DAUER_S + 0.01, [])
    assert ergebnis.zustand is Zustand.CAPTURE

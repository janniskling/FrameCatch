"""Zentrale Konfiguration von FrameCatch.

Alle Schwellwerte, Zeiten, Farben und Pfade liegen hier, damit kein
Magic Number im restlichen Code steht.
"""

# --- Kamera / Fenster -------------------------------------------------------
KAMERA_INDEX: int = 0
FENSTER_NAME: str = "FrameCatch"
TASTE_BEENDEN: str = "q"

# --- Pinch-Erkennung --------------------------------------------------------
# Pinch, wenn die Distanz Daumenspitze (Landmark 4) <-> Zeigefingerspitze
# (Landmark 8) kleiner ist als PINCH_VERHAELTNIS * Handgroesse. Die
# Handgroesse ist die Distanz Handgelenk (0) <-> Mittelfinger-Ansatz (9),
# dadurch funktioniert die Erkennung unabhaengig vom Abstand zur Kamera.
PINCH_VERHAELTNIS: float = 0.25
# Untergrenze in Pixeln, damit die Schwelle bei weit entfernter Hand
# nicht unerreichbar klein wird.
PINCH_SCHWELLE_MIN_PX: float = 30.0

# MediaPipe-Hands-Parameter
MAX_ANZAHL_HAENDE: int = 2
MIN_ERKENNUNGS_KONFIDENZ: float = 0.6
MIN_TRACKING_KONFIDENZ: float = 0.5

# --- Entprellung / Zeiten (Sekunden) ----------------------------------------
PINCH_STABIL_S: float = 0.3        # beide Haende pinchen stabil -> FRAMING
OEFFNEN_STABIL_S: float = 0.4      # beide Pinches offen stabil  -> COUNTDOWN
TRACKING_VERLUST_S: float = 0.5    # Haende verloren             -> IDLE
COUNTDOWN_DAUER_S: float = 3.0     # Countdown-Laenge bis zum Foto

# --- Rechteck ----------------------------------------------------------------
MIN_RECHTECK_PX: int = 80          # Mindestbreite und -hoehe des Ausschnitts

# --- Foto-Speicherung ---------------------------------------------------------
FOTO_ORDNER: str = "fotos"
FOTO_PREFIX: str = "foto"
JPG_QUALITAET: int = 95

# --- Sounds (macOS, abgespielt via afplay) ------------------------------------
TICK_SOUND: str = "/System/Library/Sounds/Tink.aiff"
AUSLOESE_SOUND: str = "/System/Library/Sounds/Pop.aiff"

# --- Farben (BGR) --------------------------------------------------------------
FARBE_RECHTECK: tuple[int, int, int] = (0, 200, 255)     # auffaelliges Orange/Gelb
FARBE_PINCH_PUNKT: tuple[int, int, int] = (0, 255, 0)    # Gruen
FARBE_LANDMARK: tuple[int, int, int] = (200, 200, 200)   # dezentes Grau
FARBE_LANDMARK_LINIE: tuple[int, int, int] = (130, 130, 130)
FARBE_FINGERSPITZE: tuple[int, int, int] = (255, 200, 0) # Daumen-/Zeigefingerspitze
FARBE_STATUS_TEXT: tuple[int, int, int] = (255, 255, 255)
FARBE_STATUS_SCHATTEN: tuple[int, int, int] = (0, 0, 0)
FARBE_COUNTDOWN: tuple[int, int, int] = (255, 255, 255)
FARBE_VORSCHAU_RAHMEN: tuple[int, int, int] = (255, 255, 255)

# --- Zeichnen-Details -----------------------------------------------------------
RECHTECK_LINIENSTAERKE: int = 3
PINCH_PUNKT_RADIUS: int = 10
LANDMARK_RADIUS: int = 4
FINGERSPITZEN_RADIUS: int = 7
LANDMARK_LINIENSTAERKE: int = 1
STATUS_SCHRIFT_GROESSE: float = 0.7
COUNTDOWN_SCHRIFT_GROESSE: float = 6.0
COUNTDOWN_LINIENSTAERKE: int = 12

# --- Blitz-Effekt -----------------------------------------------------------------
BLITZ_FRAMES: int = 4              # Anzahl Frames mit weissem Overlay
BLITZ_START_DECKKRAFT: float = 0.9 # Deckkraft im ersten Frame, faellt linear ab

# --- Foto-Vorschau ------------------------------------------------------------------
VORSCHAU_DAUER_S: float = 4.0      # Anzeigedauer des Thumbnails (Zeit zum Klicken)
VORSCHAU_MAX_BREITE_ANTEIL: float = 0.35  # max. Anteil der Fensterbreite
VORSCHAU_RAND_PX: int = 16         # Abstand zum Fensterrand
VORSCHAU_RAHMEN_PX: int = 3        # Rahmenstaerke um das Thumbnail
VORSCHAU_KLICK_HINWEIS: str = "Klicken zum Oeffnen"

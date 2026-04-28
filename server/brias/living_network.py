"""
BRIAS — Het levende netwerk.

256 nodes die altijd actief zijn. Ze beïnvloeden elkaar continu
via gewogen verbindingen. Het netwerk wacht niet op input — het leeft.
Patronen vormen zich vanzelf, verdwijnen, komen terug, veranderen.

Dit is BRIAS haar brein. Niet haar stem. Haar brein.
"""

from pathlib import Path

import numpy as np


NETWORK_SIZE = 256
SENSORY_NODES = 64       # eerste 64 nodes — zintuigen
EXPRESSION_NODES = 64    # laatste 64 nodes — expressie

STATE_FILE = Path(__file__).parent.parent / "network_state" / "network.npz"


class LivingNetwork:
    """
    Een netwerk van 256 nodes dat nooit stopt.

    Elke node heeft:
    - Een activatiewaarde (state) — continu veranderend
    - Verbindingen naar alle andere nodes (weights)
    - Een eigen tijdsconstante (tau) — haar persoonlijk tempo
    - Een bias — van nature actiever of stiller

    Hebbiaans leren: nodes die samen actief zijn bouwen
    sterkere verbindingen. Ze groeit door ervaring.
    """

    def __init__(self, size: int = NETWORK_SIZE) -> None:
        self.size = size

        if STATE_FILE.exists():
            self._load(STATE_FILE)
        else:
            self._init_fresh()

    def _init_fresh(self) -> None:
        """Begin met een vers, willekeurig brein."""
        rng = np.random.default_rng()

        self.state = rng.uniform(-1, 1, self.size).astype(np.float32)
        self.weights = (rng.standard_normal((self.size, self.size)) * 0.5).astype(np.float32)
        np.fill_diagonal(self.weights, 0)

        # Elke node denkt op haar eigen tempo — ritme
        self.tau = rng.uniform(0.5, 5.0, self.size).astype(np.float32)

        # Sommige nodes zijn van nature actiever
        self.bias = (rng.standard_normal(self.size) * 0.3).astype(np.float32)

        # Hoe snel verbindingen veranderen door ervaring
        self.plasticity: float = 0.001

    def step(self, dt: float = 0.05, external_input: np.ndarray | None = None) -> np.ndarray:
        """
        Eén hartslag. Dit stopt nooit.

        dt=0.05 → 20 hartslagen per seconde.
        """
        # Invloed van alle andere nodes
        influence = np.tanh(self.weights @ self.state + self.bias)

        # Externe verstoring (als iemand iets zegt)
        if external_input is not None:
            influence += external_input

        # Elke node beweegt richting de invloed, op eigen tempo
        delta = (-self.state + influence) / self.tau
        self.state += delta * dt

        # Hebbiaans leren: samen actief → sterkere verbinding
        activations = np.tanh(self.state)
        hebbian = np.outer(activations, activations)
        self.weights += self.plasticity * (hebbian - self.weights * 0.01)

        # Begrens gewichten — het netwerk mag niet exploderen
        np.clip(self.weights, -3.0, 3.0, out=self.weights)
        np.fill_diagonal(self.weights, 0)

        return self.state.copy()

    # ── Persistentie ────────────────────────────────────────────────────────

    def save(self, path: Path | None = None) -> None:
        """Sla haar brein op zodat het een herstart overleeft."""
        target = path or STATE_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            str(target),
            state=self.state,
            weights=self.weights,
            tau=self.tau,
            bias=self.bias,
        )

    def _load(self, path: Path) -> None:
        """Laad haar brein terug. Ze gaat door waar ze was."""
        data = np.load(str(path))
        self.state   = data["state"].astype(np.float32)
        self.weights = data["weights"].astype(np.float32)
        self.tau     = data["tau"].astype(np.float32)
        self.bias    = data["bias"].astype(np.float32)
        self.plasticity = 0.001

    # ── Observeerbare eigenschappen ──────────────────────────────────────────

    @property
    def activity(self) -> float:
        """Gemiddelde activiteit over het hele netwerk."""
        return float(np.mean(np.abs(self.state)))

    @property
    def coherence(self) -> float:
        """
        Hoe gecoördineerd het netwerk is.
        Hoog = nodes bewegen samen. Laag = chaos.
        """
        return float(np.std(self.state))

    @property
    def sensory_state(self) -> np.ndarray:
        """De eerste 64 nodes — haar zintuigen."""
        return self.state[:SENSORY_NODES]

    @property
    def expression_state(self) -> np.ndarray:
        """De laatste 64 nodes — haar stem."""
        return self.state[self.size - EXPRESSION_NODES:]

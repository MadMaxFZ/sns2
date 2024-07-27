
# SPACEFLIGHT NAVIGATION SIMULATOR
- A framework to simulate orbital mechanics with advanced navigation interfaces.

## DESIGN ELEMENTS
- The simulation is composed of two primary elements: The Model and the Viewer:

### MODEL OVERVIEW
- The model is implemented within its own process in order to increase performance.
- It takes commands via a command queue, emits responses via a result queue, and exposes   
  the state of the model in one or more SharedMemory segments.
- The model accepts and processes commands it receives through the command queue and
  reacts to appropriate signals.
- The model sends out responses as requested and emits signals to indicate its state to   
  other components of the simulation to synchronize their operations.

### VIEWER OVERVIEW

from util import create_state_machines
from matrix import LEDMatrix
import constants

data_sm, row_sm = create_state_machines()
matrix = LEDMatrix(data_sm, row_sm)
matrix.start(constants.TEST_PATTERN_32BIT)

# Both PIO state machines handle display timing autonomously.
# Main loop just keeps the FIFOs fed and is otherwise free for application logic.
while True:
    matrix.refill()

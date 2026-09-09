/**
 * A per-cell Run button for RISE slideshows.
 *
 * Why this exists
 * ---------------
 * RISE renders the notebook itself, but it does not ship JupyterLab's cell
 * toolbar (`@jupyterlab/cell-toolbar-extension` is absent from the Rise app
 * bundle), so a slideshow has no clickable way to run a cell -- only the
 * keyboard. During a lecture that is awkward.
 *
 * Why a real extension rather than injected JavaScript
 * ---------------------------------------------------
 * The Rise app does not expose JupyterLab's command registry on `window`, so
 * page-level scripts can only *simulate* a keystroke and hope Lumino resolves
 * it. Running as an extension gives us the genuine `commands.execute`.
 *
 * Why the slide does not jump when you click
 * ------------------------------------------
 * RISE keeps the deck in sync with the active cell:
 *
 *     panel.content.activeCellChanged.connect((sender, cell) => {
 *       const slide = Reveal.getSlides().find(s => s.contains(cell.node));
 *       if (slide) { Reveal.slide(...) }
 *     });
 *
 * That is what made Shift+Enter (`run-cell-and-select-next`) advance the deck.
 * Here we set the active cell to the one whose button was clicked -- a cell that
 * is by definition already on the visible slide -- so the handler navigates to
 * the slide it is already on, which is a no-op. We then run
 * `notebook:run-cell`, which does not move the selection.
 *
 * Pending input, and why this course needs to handle it
 * ----------------------------------------------------
 * CS 1 is a course about `input()`. Nearly every lecture runs a cell that stops
 * and waits for the class to type an answer, and a while-loop demo can sit at a
 * prompt indefinitely.
 *
 * JupyterLab guards against kernel deadlock: while any cell is waiting on stdin,
 * running a *different* cell is refused outright with
 *
 *     "Cell not executed due to pending input -- The cell has not been executed
 *      to avoid kernel deadlock as there is another pending input! Type your
 *      input in the input box, press Enter and try again."
 *
 * Mid-lecture that is a dead end: the presenter has moved on two slides, the
 * prompt that is blocking them is off-screen behind them, and nothing on the
 * current slide will run until they find it. There is no setting to relax this
 * -- the check is unconditional inside `NotebookActions` -- so this extension
 * resolves it from the front:
 *
 *   1. The waiting cell's button becomes a **stop button** (the canonical square
 *      in a circle). Clicking it interrupts the kernel, which raises
 *      KeyboardInterrupt inside `input()` and ends that cell -- the direct,
 *      visible way out.
 *
 *   2. Clicking **run** on any other cell while a prompt is pending interrupts
 *      the waiting cell first, waits for the pending-input flag to clear, and
 *      then runs the cell you actually clicked. So the click does what the
 *      presenter meant instead of raising a dialog.
 *
 * Both paths go through `kernel.interrupt()`, which leaves a KeyboardInterrupt
 * traceback on the abandoned cell. That is deliberate: it is honest about what
 * happened, and re-running that cell from the top is always safe.
 *
 * The APIs used here are all public in JupyterLab 4:
 * `CodeCell.outputArea.pendingInput`, `OutputArea.inputRequested`,
 * `IStdin.value` and `Kernel.IKernelConnection.interrupt()`.
 */

import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { Cell, CodeCell } from '@jupyterlab/cells';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';

const BUTTON_CLASS = 'dma-run-button';
const RUNNING_CLASS = 'dma-run-button-busy';
const STOP_CLASS = 'dma-run-button-stop';

/** `notebook:run-cell` runs the active cell and leaves the selection alone. */
const RUN_COMMAND = 'notebook:run-cell';

const PLAY_ICON =
  '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" ' +
  'focusable="false"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg>';

/**
 * The canonical "stop" glyph. The button is already a circle, so the icon is
 * just the square that sits inside it, with rounded corners to match.
 */
const STOP_ICON =
  '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true" ' +
  'focusable="false"><rect x="6" y="6" width="12" height="12" rx="2" ' +
  'fill="currentColor"/></svg>';

const RUN_TITLE = 'Run this cell';
const STOP_TITLE = 'Stop this cell (it is waiting for input)';

/** The cell currently blocking the kernel on stdin, if any. */
function pendingInputCell(panel: NotebookPanel): CodeCell | null {
  for (const widget of panel.content.widgets) {
    if (widget instanceof CodeCell && widget.outputArea.pendingInput) {
      return widget;
    }
  }
  return null;
}

/**
 * Interrupt the kernel. A failure here is not worth interrupting a lecture for
 * -- the worst case is that JupyterLab shows its own pending-input dialog,
 * which is the behaviour we already had.
 */
async function interruptKernel(panel: NotebookPanel): Promise<void> {
  const kernel = panel.sessionContext.session?.kernel;
  if (!kernel) {
    return;
  }
  try {
    await kernel.interrupt();
  } catch {
    /* fall through and let the run attempt report whatever is wrong */
  }
}

/**
 * Wait for the pending-input flag to clear after an interrupt.
 *
 * `kernel.interrupt()` resolves when the interrupt has been *delivered*, not
 * when the cell has finished unwinding, so running immediately afterwards can
 * still trip the guard. Bounded by a timeout so a wedged kernel can never hang
 * a click: if it expires we run anyway and let JupyterLab report the problem.
 */
async function waitForPendingInputToClear(
  panel: NotebookPanel,
  timeoutMs = 3000
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (pendingInputCell(panel) && Date.now() < deadline) {
    await new Promise(resolve => window.setTimeout(resolve, 50));
  }
}

function setStopMode(button: HTMLButtonElement, stop: boolean): void {
  button.classList.toggle(STOP_CLASS, stop);
  button.innerHTML = stop ? STOP_ICON : PLAY_ICON;
  const title = stop ? STOP_TITLE : RUN_TITLE;
  button.title = title;
  button.setAttribute('aria-label', title);
}

/**
 * Hold the button in stop mode for exactly as long as this cell is waiting.
 *
 * Polled rather than driven off `IStdin.value`, because that promise settles
 * when the input is *submitted* and never settles when the cell is interrupted
 * instead -- which is the case this whole feature exists for. Reading a boolean
 * every 100ms costs nothing and cannot get stuck in the wrong state.
 */
async function holdStopModeWhileWaiting(
  cell: CodeCell,
  button: HTMLButtonElement
): Promise<void> {
  setStopMode(button, true);
  while (!cell.isDisposed && cell.outputArea.pendingInput) {
    await new Promise(resolve => window.setTimeout(resolve, 100));
  }
  if (!cell.isDisposed) {
    setStopMode(button, false);
  }
}

function addButton(
  app: JupyterFrontEnd,
  panel: NotebookPanel,
  cell: Cell
): void {
  if (!(cell instanceof CodeCell)) {
    return;
  }
  // Cell widgets are reused as RISE moves their nodes between slides, so a
  // button added once travels with the cell. Never add a second one.
  if (cell.node.querySelector(`.${BUTTON_CLASS}`)) {
    return;
  }

  const button = document.createElement('button');
  button.className = BUTTON_CLASS;
  button.type = 'button';
  button.innerHTML = PLAY_ICON;
  button.title = RUN_TITLE;
  button.setAttribute('aria-label', RUN_TITLE);

  // Flip to a stop button for as long as this cell holds the stdin prompt.
  cell.outputArea.inputRequested.connect(() => {
    void holdStopModeWhileWaiting(cell, button);
  });

  button.addEventListener('click', async (event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();

    // Stop mode: this is the cell holding the prompt, so the button's job is to
    // end it, not to start it again.
    if (button.classList.contains(STOP_CLASS)) {
      await interruptKernel(panel);
      return;
    }

    const index = panel.content.widgets.indexOf(cell);
    if (index < 0) {
      return;
    }

    // Some other cell is parked on a prompt, so JupyterLab would refuse to run
    // this one. Clear the blockage first; see the header for why.
    if (pendingInputCell(panel)) {
      await interruptKernel(panel);
      await waitForPendingInputToClear(panel);
    }

    panel.content.activeCellIndex = index;

    // The button replaces the `[ ]:` prompt in slideshow mode, so it also has
    // to carry the "this is running" signal the prompt would have given.
    button.classList.add(RUNNING_CLASS);
    try {
      await app.commands.execute(RUN_COMMAND);
    } finally {
      button.classList.remove(RUNNING_CLASS);
    }
  });

  cell.node.appendChild(button);
}

function decorate(app: JupyterFrontEnd, panel: NotebookPanel): void {
  panel.content.widgets.forEach(cell => addButton(app, panel, cell));
}

const plugin: JupyterFrontEndPlugin<void> = {
  id: 'dma-rise-run-button:plugin',
  description: 'Adds a Run button to every code cell in a RISE slideshow.',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (app: JupyterFrontEnd, tracker: INotebookTracker): void => {
    const track = (panel: NotebookPanel): void => {
      void panel.revealed.then(() => {
        decorate(app, panel);
        // Cells added or removed later (including while presenting) still get
        // a button. Deferred so the widget exists by the time we look for it.
        panel.content.model?.cells.changed.connect(() => {
          window.setTimeout(() => decorate(app, panel), 0);
        });
      });
    };

    tracker.forEach(track);
    tracker.widgetAdded.connect((_, panel) => track(panel));
  }
};

export default plugin;

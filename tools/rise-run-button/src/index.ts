/** A per-cell Run button for CS0002 RISE slideshows. */

import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { Cell, CodeCell } from '@jupyterlab/cells';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';

const BUTTON_CLASS = 'cs1-run-button';
const RUNNING_CLASS = 'cs1-run-button-busy';
const RUN_COMMAND = 'notebook:run-cell';

const PLAY_ICON =
  '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" ' +
  'focusable="false"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg>';

function addButton(
  app: JupyterFrontEnd,
  panel: NotebookPanel,
  cell: Cell
): void {
  if (!(cell instanceof CodeCell)) {
    return;
  }
  if (cell.node.querySelector(`.${BUTTON_CLASS}`)) {
    return;
  }

  const button = document.createElement('button');
  button.className = BUTTON_CLASS;
  button.type = 'button';
  button.title = 'Run this cell';
  button.setAttribute('aria-label', 'Run this cell');
  button.innerHTML = PLAY_ICON;

  button.addEventListener('click', async (event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();

    const index = panel.content.widgets.indexOf(cell);
    if (index < 0) {
      return;
    }
    panel.content.activeCellIndex = index;

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
  id: 'cs1-rise-run-button:plugin',
  description: 'Adds a Run button to every code cell in a RISE slideshow.',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (app: JupyterFrontEnd, tracker: INotebookTracker): void => {
    const track = (panel: NotebookPanel): void => {
      void panel.revealed.then(() => {
        decorate(app, panel);
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

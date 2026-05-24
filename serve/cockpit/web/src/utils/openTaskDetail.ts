export const OPEN_TASK_DETAIL_EVENT = 'cockpit:open-task-detail'

interface OpenTaskDetailEventDetail {
  taskId: number
}

export function openTaskDetail(taskId: number): void {
  window.dispatchEvent(new CustomEvent<OpenTaskDetailEventDetail>(OPEN_TASK_DETAIL_EVENT, {
    detail: { taskId },
  }))
}

export function readOpenTaskDetailEvent(event: Event): number | null {
  const detail = (event as CustomEvent<OpenTaskDetailEventDetail>).detail
  const taskId = detail?.taskId
  return Number.isInteger(taskId) && taskId >= 0 ? taskId : null
}

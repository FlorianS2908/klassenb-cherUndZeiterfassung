import { useEffect, useState } from 'react';
import type { AnalysisResult, KlassenbuchEntry, UeItem, UploadedFileInfo } from '../types';

export type WorkflowStep = 'overview' | 'classbooks' | 'analysis' | 'review' | 'submit_done';

export type WorkflowEntry = UeItem & {
  index: number;
  title?: string;
  approved: boolean;
};

export type WorkflowState = {
  currentStep: WorkflowStep;
  selectedClassbook: null | KlassenbuchEntry;
  uploadedFile: null | {
    name: string;
    path?: string;
    type?: string;
  };
  selectedRange: string;
  analysisResult: null | AnalysisResult;
  generatedEntries: WorkflowEntry[];
  analysisDone: boolean;
  reviewConfirmed: boolean;
  signatureReady: boolean;
  reviewDone: boolean;
};

const STORAGE_KEY = 'klassenbuch.workflow.v1';

export const initialWorkflowState: WorkflowState = {
  currentStep: 'overview',
  selectedClassbook: null,
  uploadedFile: null,
  selectedRange: '',
  analysisResult: null,
  generatedEntries: [],
  analysisDone: false,
  reviewConfirmed: false,
  signatureReady: false,
  reviewDone: false,
};

function loadWorkflowState(): WorkflowState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return initialWorkflowState;
    return { ...initialWorkflowState, ...JSON.parse(raw) };
  } catch {
    return initialWorkflowState;
  }
}

export function normalizeEntries(items: UeItem[]): WorkflowEntry[] {
  return items.map((item, index) => ({
    ...item,
    index: index + 1,
    approved: false,
  }));
}

export function uploadedFileFromInfo(file: UploadedFileInfo | null) {
  if (!file) return null;
  return { name: file.filename, type: file.file_type, path: file.file_id };
}

export function useWorkflowState() {
  const [workflow, setWorkflow] = useState<WorkflowState>(loadWorkflowState());

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(workflow));
  }, [workflow]);

  function updateWorkflow(patch: Partial<WorkflowState>) {
    setWorkflow((current) => ({ ...current, ...patch }));
  }

  function resetWorkflow() {
    setWorkflow(initialWorkflowState);
    localStorage.removeItem(STORAGE_KEY);
  }

  return { workflow, setWorkflow: updateWorkflow, resetWorkflow };
}

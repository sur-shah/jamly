export type CustomExercisePayload = {
  user_id: number;
  title: string;
  instrument: "guitar";
  genre: "pop" | "blues" | "jazz" | "rock" | "rnb";
  level: "beginner" | "intermediate" | "advanced";
  focus: "chords" | "scales" | "rhythm" | "ear_training";
  key: string;
  tempo_bpm: number;
  chord_progression: string[];
};

export type Exercise = CustomExercisePayload & {
  id: number;
  steps: Array<{ minutes: number; label: string }>;
  target_analysis: {
    expected_chords?: string[];
    required_tones?: Record<string, string[]>;
  };
};

export type PracticeSession = {
  id: number;
  user_id: number;
  exercise_id: number;
  status: string;
  started_at: string;
  completed_at: string | null;
};

export type Recording = {
  id: number;
  practice_session_id: number;
  original_filename: string;
  content_type: string;
  status: string;
  created_at: string;
};

export type ChordFeedback = {
  expected: string;
  detected?: string | null;
  status: string;
  detected_tones?: string[];
  required_tones?: string[];
  missing_tones?: string[];
  extra_tones?: string[];
  start_seconds?: number;
  end_seconds?: number;
};

export type FeedbackReport = {
  id: number;
  practice_session_id: number;
  recording_id: number;
  score: number;
  summary: string;
  main_fix: string;
  practice_tip: string;
  analysis: {
    chords?: ChordFeedback[];
    notes?: {
      status: string;
      count?: number;
      pitch_classes?: string[];
    };
    tempo?: {
      target_bpm: number;
      estimated_bpm: number | null;
      status: string;
    };
  };
  created_at: string;
};

export type RecordingUploadResponse = {
  recording: Recording;
  feedback_report: FeedbackReport | null;
  message: string;
};

const DEFAULT_API_URL = "http://127.0.0.1:8000";

export const API_URL = process.env.EXPO_PUBLIC_API_URL || DEFAULT_API_URL;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function createCustomExercise(payload: CustomExercisePayload): Promise<Exercise> {
  return request<Exercise>("/exercises/custom", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createPracticeSession(userId: number, exerciseId: number): Promise<PracticeSession> {
  return request<PracticeSession>("/practice-sessions", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, exercise_id: exerciseId }),
  });
}

export function uploadRecording(
  practiceSessionId: number,
  file: { uri: string; name: string; mimeType?: string },
): Promise<RecordingUploadResponse> {
  const formData = new FormData();
  formData.append("file", {
    uri: file.uri,
    name: file.name,
    type: file.mimeType || "audio/mpeg",
  } as unknown as Blob);

  return request<RecordingUploadResponse>(`/practice-sessions/${practiceSessionId}/recordings`, {
    method: "POST",
    body: formData,
  });
}

export function analyzeRecording(
  practiceSessionId: number,
  recordingId: number,
): Promise<RecordingUploadResponse> {
  return request<RecordingUploadResponse>(
    `/practice-sessions/${practiceSessionId}/recordings/${recordingId}/analyze`,
    { method: "POST" },
  );
}

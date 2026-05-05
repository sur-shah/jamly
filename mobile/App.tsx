import { Ionicons } from "@expo/vector-icons";
import * as DocumentPicker from "expo-document-picker";
import { StatusBar } from "expo-status-bar";
import { ReactNode, useMemo, useState } from "react";
import {
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import {
  API_URL,
  ChordFeedback,
  createCustomExercise,
  createPracticeSession,
  Exercise,
  FeedbackReport,
  PracticeSession,
  uploadRecording,
} from "./src/api";

const USER_ID = 1;
const DEFAULT_PROGRESSION = "Em, C, G, D";

export default function App() {
  const [title, setTitle] = useState("Four Chord Guitar Progression");
  const [keyName, setKeyName] = useState("G");
  const [tempo, setTempo] = useState("80");
  const [progression, setProgression] = useState(DEFAULT_PROGRESSION);
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [practiceSession, setPracticeSession] = useState<PracticeSession | null>(null);
  const [feedback, setFeedback] = useState<FeedbackReport | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const chords = useMemo(
    () =>
      progression
        .split(",")
        .map((chord) => chord.trim())
        .filter(Boolean),
    [progression],
  );

  async function handleCreateExercise() {
    if (chords.length === 0) {
      Alert.alert("Add chords", "Enter at least one chord.");
      return;
    }

    setIsBusy(true);
    setFeedback(null);
    try {
      const createdExercise = await createCustomExercise({
        user_id: USER_ID,
        title,
        instrument: "guitar",
        genre: "pop",
        level: "beginner",
        focus: "chords",
        key: keyName,
        tempo_bpm: Number(tempo) || 80,
        chord_progression: chords,
      });
      const createdSession = await createPracticeSession(USER_ID, createdExercise.id);
      setExercise(createdExercise);
      setPracticeSession(createdSession);
    } catch (error) {
      showError(error);
    } finally {
      setIsBusy(false);
    }
  }

  async function handlePickAndUpload() {
    if (!practiceSession) {
      Alert.alert("Create a session first", "Create the exercise before uploading audio.");
      return;
    }

    const result = await DocumentPicker.getDocumentAsync({
      type: ["audio/*", "video/*"],
      copyToCacheDirectory: true,
    });

    if (result.canceled || !result.assets[0]) {
      return;
    }

    const asset = result.assets[0];
    setSelectedFileName(asset.name);
    setIsBusy(true);

    try {
      const uploadResult = await uploadRecording(practiceSession.id, {
        uri: asset.uri,
        name: asset.name,
        mimeType: asset.mimeType,
      });
      setFeedback(uploadResult.feedback_report);
    } catch (error) {
      showError(error);
    } finally {
      setIsBusy(false);
    }
  }

  function resetFlow() {
    setExercise(null);
    setPracticeSession(null);
    setFeedback(null);
    setSelectedFileName(null);
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <View style={styles.logo}>
            <Ionicons color="#14130F" name="musical-notes" size={24} />
          </View>
          <View>
            <Text style={styles.appName}>Jamly</Text>
            <Text style={styles.apiText}>{API_URL}</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Practice Setup</Text>
          <LabeledInput label="Title" value={title} onChangeText={setTitle} />
          <View style={styles.row}>
            <View style={styles.rowItem}>
              <LabeledInput label="Key" value={keyName} onChangeText={setKeyName} />
            </View>
            <View style={styles.rowItem}>
              <LabeledInput
                label="Tempo"
                value={tempo}
                onChangeText={setTempo}
                keyboardType="number-pad"
              />
            </View>
          </View>
          <LabeledInput label="Chords" value={progression} onChangeText={setProgression} />
          <View style={styles.chipRow}>
            {chords.map((chord) => (
              <View key={chord} style={styles.chip}>
                <Text style={styles.chipText}>{chord}</Text>
              </View>
            ))}
          </View>
        </View>

        <View style={styles.actions}>
          <ActionButton
            icon={<Ionicons color="#FFFFFF" name="play" size={18} />}
            label={practiceSession ? "Session Ready" : "Create Session"}
            onPress={handleCreateExercise}
            disabled={isBusy}
            variant="primary"
          />
          <ActionButton
            icon={<Ionicons color="#14130F" name="cloud-upload-outline" size={18} />}
            label="Upload Take"
            onPress={handlePickAndUpload}
            disabled={isBusy || !practiceSession}
            variant="secondary"
          />
          <Pressable style={styles.iconButton} onPress={resetFlow} disabled={isBusy}>
            <Ionicons color="#14130F" name="refresh" size={19} />
          </Pressable>
        </View>

        {isBusy ? (
          <View style={styles.loading}>
            <Ionicons color="#2F6F62" name="sync" size={20} />
            <Text style={styles.loadingText}>Working with the backend...</Text>
          </View>
        ) : null}

        {exercise ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Exercise</Text>
            <Text style={styles.bodyText}>
              {exercise.title} at {exercise.tempo_bpm} BPM
            </Text>
            {exercise.steps.map((step) => (
              <Text key={step.label} style={styles.stepText}>
                {step.minutes} min: {step.label}
              </Text>
            ))}
          </View>
        ) : null}

        {selectedFileName ? (
          <View style={styles.fileRow}>
            <Ionicons color="#2F6F62" name="document-attach-outline" size={18} />
            <Text style={styles.fileText}>{selectedFileName}</Text>
          </View>
        ) : null}

        {feedback ? <FeedbackCard feedback={feedback} /> : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function FeedbackCard({ feedback }: { feedback: FeedbackReport }) {
  const chords = feedback.analysis.chords || [];

  return (
    <View style={styles.feedback}>
      <View style={styles.scoreRow}>
        <Text style={styles.feedbackTitle}>Feedback</Text>
        <View style={styles.scorePill}>
          <Text style={styles.scoreText}>{feedback.score}</Text>
        </View>
      </View>
      <Text style={styles.summary}>{feedback.summary}</Text>
      <Text style={styles.fix}>{feedback.main_fix}</Text>
      <Text style={styles.tip}>{feedback.practice_tip}</Text>

      {chords.length > 0 ? (
        <View style={styles.chordList}>
          {chords.map((chord, index) => (
            <ChordRow chord={chord} key={`${chord.expected}-${index}`} />
          ))}
        </View>
      ) : null}
    </View>
  );
}

function ChordRow({ chord }: { chord: ChordFeedback }) {
  return (
    <View style={styles.chordRow}>
      <View style={styles.chordHeading}>
        <Text style={styles.chordName}>{chord.expected}</Text>
        <Text style={styles.chordStatus}>{chord.status.replaceAll("_", " ")}</Text>
      </View>
      <Text style={styles.chordDetail}>Detected: {formatList(chord.detected_tones)}</Text>
      <Text style={styles.chordDetail}>Missing: {formatList(chord.missing_tones)}</Text>
      <Text style={styles.chordDetail}>Extra: {formatList(chord.extra_tones)}</Text>
    </View>
  );
}

function LabeledInput({
  label,
  value,
  onChangeText,
  keyboardType,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "number-pad";
}) {
  return (
    <View style={styles.inputGroup}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
      />
    </View>
  );
}

function ActionButton({
  icon,
  label,
  onPress,
  disabled,
  variant,
}: {
  icon: ReactNode;
  label: string;
  onPress: () => void;
  disabled?: boolean;
  variant: "primary" | "secondary";
}) {
  return (
    <Pressable
      style={[
        styles.actionButton,
        variant === "primary" ? styles.primaryButton : styles.secondaryButton,
        disabled ? styles.disabledButton : null,
      ]}
      onPress={onPress}
      disabled={disabled}
    >
      {icon}
      <Text style={variant === "primary" ? styles.primaryButtonText : styles.secondaryButtonText}>
        {label}
      </Text>
    </Pressable>
  );
}

function formatList(values?: string[]) {
  return values && values.length > 0 ? values.join(", ") : "none";
}

function showError(error: unknown) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  Alert.alert("Jamly API error", message);
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#F7F4EE",
  },
  container: {
    gap: 18,
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
    paddingTop: 10,
  },
  logo: {
    alignItems: "center",
    backgroundColor: "#DDEFE7",
    borderRadius: 8,
    height: 48,
    justifyContent: "center",
    width: 48,
  },
  appName: {
    color: "#14130F",
    fontSize: 26,
    fontWeight: "800",
    letterSpacing: 0,
  },
  apiText: {
    color: "#6E6A61",
    fontSize: 12,
    marginTop: 2,
  },
  section: {
    backgroundColor: "#FFFFFF",
    borderColor: "#E2DED5",
    borderRadius: 8,
    borderWidth: 1,
    gap: 12,
    padding: 16,
  },
  sectionTitle: {
    color: "#14130F",
    fontSize: 18,
    fontWeight: "800",
    letterSpacing: 0,
  },
  inputGroup: {
    gap: 6,
  },
  label: {
    color: "#565249",
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  input: {
    backgroundColor: "#FAF9F5",
    borderColor: "#D8D2C6",
    borderRadius: 6,
    borderWidth: 1,
    color: "#14130F",
    fontSize: 16,
    minHeight: 46,
    paddingHorizontal: 12,
  },
  row: {
    flexDirection: "row",
    gap: 12,
  },
  rowItem: {
    flex: 1,
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  chip: {
    backgroundColor: "#EAF4EF",
    borderColor: "#B8D7C8",
    borderRadius: 6,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  chipText: {
    color: "#255B50",
    fontSize: 13,
    fontWeight: "800",
  },
  actions: {
    alignItems: "center",
    flexDirection: "row",
    gap: 10,
  },
  actionButton: {
    alignItems: "center",
    borderRadius: 7,
    flex: 1,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    minHeight: 48,
    paddingHorizontal: 12,
  },
  primaryButton: {
    backgroundColor: "#2F6F62",
  },
  secondaryButton: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D2C6",
    borderWidth: 1,
  },
  disabledButton: {
    opacity: 0.45,
  },
  primaryButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "800",
  },
  secondaryButtonText: {
    color: "#14130F",
    fontSize: 14,
    fontWeight: "800",
  },
  iconButton: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D2C6",
    borderRadius: 7,
    borderWidth: 1,
    height: 48,
    justifyContent: "center",
    width: 48,
  },
  loading: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
  },
  loadingText: {
    color: "#565249",
    fontSize: 14,
  },
  bodyText: {
    color: "#292720",
    fontSize: 15,
    lineHeight: 22,
  },
  stepText: {
    color: "#565249",
    fontSize: 14,
    lineHeight: 20,
  },
  fileRow: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#E2DED5",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 8,
    padding: 12,
  },
  fileText: {
    color: "#292720",
    flex: 1,
    fontSize: 14,
  },
  feedback: {
    backgroundColor: "#14130F",
    borderRadius: 8,
    gap: 12,
    padding: 16,
  },
  scoreRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  feedbackTitle: {
    color: "#FFFFFF",
    fontSize: 20,
    fontWeight: "800",
    letterSpacing: 0,
  },
  scorePill: {
    alignItems: "center",
    backgroundColor: "#DDEFE7",
    borderRadius: 6,
    minWidth: 48,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  scoreText: {
    color: "#12362F",
    fontSize: 16,
    fontWeight: "900",
  },
  summary: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
    lineHeight: 23,
  },
  fix: {
    color: "#F4DFA1",
    fontSize: 15,
    lineHeight: 22,
  },
  tip: {
    color: "#D3D0C8",
    fontSize: 14,
    lineHeight: 21,
  },
  chordList: {
    gap: 10,
    marginTop: 4,
  },
  chordRow: {
    backgroundColor: "#23211B",
    borderColor: "#39362E",
    borderRadius: 7,
    borderWidth: 1,
    gap: 6,
    padding: 12,
  },
  chordHeading: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  chordName: {
    color: "#FFFFFF",
    fontSize: 18,
    fontWeight: "900",
  },
  chordStatus: {
    color: "#DDEFE7",
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  chordDetail: {
    color: "#D3D0C8",
    fontSize: 13,
    lineHeight: 19,
  },
});

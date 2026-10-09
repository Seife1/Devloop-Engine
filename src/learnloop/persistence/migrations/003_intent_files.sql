CREATE TABLE intent_files (
  intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
  path TEXT NOT NULL,
  touched INTEGER,
  PRIMARY KEY (intent_id, path)
);

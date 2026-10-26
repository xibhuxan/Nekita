-- Esquema inicial (spec 7.2). Las migraciones solo van hacia delante.

CREATE TABLE chats (            -- grupo que alguna vez generó actividad
  chat_id     INTEGER PRIMARY KEY,
  title       TEXT,
  first_seen  TEXT NOT NULL,    -- ISO-8601 UTC
  last_seen   TEXT NOT NULL
) STRICT;

CREATE TABLE users (            -- el nombre visible es solo para mostrar
  user_id     INTEGER PRIMARY KEY,
  display     TEXT NOT NULL,
  updated_at  TEXT NOT NULL
) STRICT;

CREATE TABLE pole_wins (        -- una fila por puesto ganado: fuente de verdad
  chat_id   INTEGER NOT NULL REFERENCES chats(chat_id),
  game_id   TEXT    NOT NULL,   -- id de games.toml
  day_key   TEXT    NOT NULL,   -- 'YYYY-MM-DD' local en la zona de ese juego
  position  INTEGER NOT NULL CHECK (position >= 0),
  user_id   INTEGER NOT NULL REFERENCES users(user_id),
  points    INTEGER NOT NULL CHECK (points >= 0),   -- los de ese momento
  won_at    TEXT    NOT NULL,   -- instante UTC del mensaje
  PRIMARY KEY (chat_id, game_id, day_key, position),
  UNIQUE      (chat_id, game_id, day_key, user_id)
) STRICT;
CREATE INDEX ix_pole_wins_ranking ON pole_wins (chat_id, game_id, user_id);

CREATE TABLE pole_legacy (      -- puntos de Node v1 (por nombre) sin reclamar
  chat_id  INTEGER NOT NULL REFERENCES chats(chat_id),
  game_id  TEXT    NOT NULL,
  name     TEXT    NOT NULL,
  points   INTEGER NOT NULL CHECK (points >= 0),
  PRIMARY KEY (chat_id, game_id, name)
) STRICT;

CREATE TABLE pole_adjust (      -- puntos importados o reclamados del legado
  chat_id  INTEGER NOT NULL REFERENCES chats(chat_id),
  game_id  TEXT    NOT NULL,
  user_id  INTEGER NOT NULL REFERENCES users(user_id),
  points   INTEGER NOT NULL,
  PRIMARY KEY (chat_id, game_id, user_id)
) STRICT;

CREATE TABLE stats (            -- solo contadores de comandos: 'cmd:neko'
  key    TEXT PRIMARY KEY,
  count  INTEGER NOT NULL DEFAULT 0
) STRICT;

CREATE TABLE nekomando_overrides (   -- editables en caliente (Fase 4)
  phrase    TEXT PRIMARY KEY,        -- ya normalizada
  response  TEXT NOT NULL
) STRICT;

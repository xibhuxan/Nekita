-- Registro de grupos desde el primer mensaje y alta/baja del bot, e historial de anuncios.

ALTER TABLE chats ADD COLUMN kind TEXT;                 -- 'group' | 'supergroup' | NULL (importado)
ALTER TABLE chats ADD COLUMN active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1));

CREATE TABLE announcements (
  id          INTEGER PRIMARY KEY,
  admin_id    INTEGER NOT NULL,
  created_at  TEXT    NOT NULL,   -- ISO-8601 UTC
  scope       TEXT    NOT NULL CHECK (scope IN ('all', 'some')),
  total       INTEGER NOT NULL,
  ok          INTEGER NOT NULL,
  failed      INTEGER NOT NULL,
  preview     TEXT    NOT NULL    -- primeros caracteres, para el historial
) STRICT;

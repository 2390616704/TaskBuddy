import { mkdir, rm } from "node:fs/promises";
import path from "node:path";

const directory = path.resolve("test-results");
const database = path.join(directory, "e2e.db");

await mkdir(directory, { recursive: true });
await Promise.all(
  [database, `${database}-shm`, `${database}-wal`].map((file) =>
    rm(file, { force: true }),
  ),
);

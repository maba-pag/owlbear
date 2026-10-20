import type { MemoriesResponse } from "../../src/api/memories";

export const EMPTY_MEMORIES = {
  entries: [],
  parse_errors: 0,
} satisfies MemoriesResponse;

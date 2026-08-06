import book from "../assets/icons/book.svg?url";
import nodes from "../assets/icons/nodes.svg?url";
import review from "../assets/icons/review.svg?url";
import search from "../assets/icons/search.svg?url";
import settings from "../assets/icons/settings.svg?url";

export const gameIconUrls = {
  book,
  nodes,
  review,
  search,
  settings,
} as const;

export type GameIconName = keyof typeof gameIconUrls;


import { request } from "../request";
import type { DailyDigestItem, ReviewQueueItem } from "../types/insights";

export const insightsApi = {
  listDailyDigests: () => request<DailyDigestItem[]>("/insights/daily-digests"),
  listReviewQueue: () => request<ReviewQueueItem[]>("/insights/review-queue"),
  createReviewQueueItem: (item: ReviewQueueItem) =>
    request<ReviewQueueItem>("/insights/review-queue", {
      method: "POST",
      body: JSON.stringify(item),
    }),
  resolveReviewQueueItem: (itemId: string, status: string, note = "") =>
    request<ReviewQueueItem>(`/insights/review-queue/${itemId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ status, note }),
    }),
};

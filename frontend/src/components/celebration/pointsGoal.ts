import { he } from "../../i18n/he";
import type { BillingPrices, SubscriptionState } from "../../types/api";

/** Something points can buy, shown as the next thing to collect toward. */
export interface PointsGoal {
  target: number;
  label: string;
  toGo: (left: number) => string;
  reached: string;
}

const c = he.celebration;

/** The subscription when it costs points (it is free while its price is 0), else featuring a posting. */
export function pointsGoal(subscription: SubscriptionState | undefined, prices: BillingPrices | undefined): PointsGoal | undefined {
  if (subscription && !subscription.free_checkout && subscription.price_points > 0) {
    return { target: subscription.price_points, label: c.goalSubscription, toGo: c.toSubscription, reached: c.subscriptionReached };
  }
  if (prices && prices.featured_job_points > 0) {
    return { target: prices.featured_job_points, label: c.goalFeatured, toGo: c.toFeatured, reached: c.featuredReached };
  }
  return undefined;
}

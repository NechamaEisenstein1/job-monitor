import type { SalaryExtra } from "../../types/salaryOffers";

export function totalSalary(baseSalary: number, extras: SalaryExtra[]): number {
  return baseSalary + extras.reduce((sum, extra) => sum + extra.amount, 0);
}

export function shareOfValuesBelow(values: number[], value: number): number {
  return values.filter((other) => other < value).length / values.length;
}

export function shareOfValuesAbove(values: number[], value: number): number {
  return values.filter((other) => other > value).length / values.length;
}

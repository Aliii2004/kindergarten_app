
export interface MonthlyReport {
  id: number;
  report_month: string;
  total_portions_served_overall: number;
  is_overall_suspicious: boolean;
  generated_at: string;
  generated_by_user: {
    username: string;
    full_name: string;
  };
  meal_performance_summaries: MealPerformanceSummary[];
  all_ingredient_usage_details: IngredientUsageDetail[];
  product_balance_summaries: ProductBalanceSummary[];
}

export interface MealPerformanceSummary {
  id: number;
  meal_id: number;
  portions_served_this_meal: number;
  possible_portions_at_report_time: number;
  difference_percentage: number;
  is_suspicious: boolean;
  meal: {
    name: string;
    description: string;
    is_active: boolean;
  } | null;
}

export interface IngredientUsageDetail {
  id: number;
  meal_id: number;
  product_id: number;
  total_quantity_used: number;
  meal_for_ingredient_detail: {
    name: string;
    description: string;
    is_active: boolean;
  };
  product_for_ingredient_detail: {
    name: string;
    unit_id: number;
    min_quantity: number;
  };
}

export interface ProductBalanceSummary {
  id: number;
  product_id: number;
  initial_stock: number;
  total_received: number;
  total_available: number;
  calculated_consumption: number;
  actual_consumption: number;
  theoretical_ending_stock: number;
  actual_ending_stock: number;
  discrepancy: number;
  discrepancy_percentage: number;
  is_balance_suspicious: boolean;
  product_in_balance: {
    name: string;
    unit_id: number;
    min_quantity: number;
  };
}

export interface IngredientConsumptionData {
  product_name: string;
  total_consumed: number;
  unit_short_name: string;
}

export interface ProductDeliveryTrend {
  delivery_date: string;
  product_name: string;
  total_delivered: number;
  unit_short_name: string;
}

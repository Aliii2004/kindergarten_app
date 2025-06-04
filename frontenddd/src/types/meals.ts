
export interface MealIngredient {
  id: number;
  product_id: number;
  quantity_per_portion: number;
  unit_id: number;
  product: {
    name: string;
    unit_id: number;
    min_quantity: number;
  };
  unit: {
    name: string;
    short_name: string;
  };
}

export interface Meal {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  ingredients: MealIngredient[];
  possible_portions?: number;
  created_by_user: {
    username: string;
    full_name: string;
  };
  created_at: string;
  updated_at: string;
}

export interface AvailableMeal {
  meal_id: number;
  meal_name: string;
  possible_portions: number;
  limiting_ingredient_name: string;
  limiting_ingredient_unit: string;
}

export interface MealServing {
  id: number;
  meal_id: number;
  portions_served: number;
  notes: string;
  served_at: string;
  meal: {
    name: string;
    description: string;
    is_active: boolean;
  };
  served_by_user: {
    username: string;
    full_name: string;
  };
  serving_details?: ServingDetail[];
}

export interface ServingDetail {
  id: number;
  product_id: number;
  quantity_used: number;
  product: {
    name: string;
    unit_id: number;
    min_quantity: number;
  };
  created_at: string;
}

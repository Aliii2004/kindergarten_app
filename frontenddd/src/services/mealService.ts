
import { api } from '@/lib/api';
import { Meal, AvailableMeal, MealServing } from '@/types/meals';

export const mealService = {
  async getMeals(params?: {
    skip?: number;
    limit?: number;
    active_only?: boolean;
    name_filter?: string;
  }) {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.active_only !== undefined) queryParams.append('active_only', params.active_only.toString());
    if (params?.name_filter) queryParams.append('name_filter', params.name_filter);

    const response = await api.get(`/api/meals/?${queryParams}`);
    return response.data;
  },

  async getMeal(mealId: number): Promise<Meal> {
    const response = await api.get(`/api/meals/${mealId}`);
    return response.data;
  },

  async createMeal(mealData: {
    name: string;
    description: string;
    is_active: boolean;
    ingredients: Array<{
      product_id: number;
      quantity_per_portion: number;
      unit_id: number;
    }>;
  }): Promise<Meal> {
    const response = await api.post('/api/meals/', mealData);
    return response.data;
  },

  async updateMeal(mealId: number, mealData: {
    name: string;
    description: string;
    is_active: boolean;
    ingredients: Array<{
      product_id: number;
      quantity_per_portion: number;
      unit_id: number;
    }>;
  }): Promise<Meal> {
    const response = await api.put(`/api/meals/${mealId}`, mealData);
    return response.data;
  },

  async deleteMeal(mealId: number): Promise<Meal> {
    const response = await api.delete(`/api/meals/${mealId}`);
    return response.data;
  },

  async getAvailableMeals(): Promise<AvailableMeal[]> {
    const response = await api.get('/api/meals/available-for-serving');
    return response.data;
  },

  async recalculatePortions() {
    const response = await api.post('/api/meals/recalculate-possible-portions/');
    return response.data;
  }
};

export const servingService = {
  async getServings(params?: {
    skip?: number;
    limit?: number;
    meal_id?: number;
    user_id?: number;
    start_date?: string;
    end_date?: string;
  }) {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.meal_id !== undefined) queryParams.append('meal_id', params.meal_id.toString());
    if (params?.user_id !== undefined) queryParams.append('user_id', params.user_id.toString());
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);

    const response = await api.get(`/api/servings/?${queryParams}`);
    return response.data;
  },

  async getServing(servingId: number): Promise<MealServing> {
    const response = await api.get(`/api/servings/${servingId}`);
    return response.data;
  },

  async createServing(servingData: {
    meal_id: number;
    portions_served: number;
    notes?: string;
  }): Promise<MealServing> {
    const response = await api.post('/api/servings/', servingData);
    return response.data;
  }
};

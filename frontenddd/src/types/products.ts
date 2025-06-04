
export interface Unit {
  id: number;
  name: string;
  short_name: string;
  created_at: string;
}

export interface Product {
  id: number;
  name: string;
  unit_id: number;
  min_quantity: number;
  unit: Unit;
  created_at: string;
  updated_at: string;
  created_by_user: {
    username: string;
    full_name: string;
  };
  current_quantity?: number;
}

export interface ProductDelivery {
  id: number;
  product_id: number;
  quantity: number;
  delivery_date: string;
  supplier: string;
  price: number;
  product_name: string | null;
  product_unit_short_name: string | null;
  received_by_user: {
    username: string;
    full_name: string;
  };
  created_at: string;
}

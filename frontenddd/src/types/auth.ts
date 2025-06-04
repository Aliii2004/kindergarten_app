
export interface User {
  id: number;
  username: string;
  full_name: string;
  role: {
    id: number;
    name: string;
    description: string;
    created_at: string;
  };
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface Role {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

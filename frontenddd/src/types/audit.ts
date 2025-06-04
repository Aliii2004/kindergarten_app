
export interface AuditLog {
  id: number;
  action: string;
  target_entity_type: string | null;
  target_entity_id: number | null;
  status: 'SUCCESS' | 'FAILURE' | 'INITIATED';
  details: string;
  changes_before: any;
  changes_after: any;
  ip_address: string;
  user_agent: string;
  timestamp: string;
  user_id: number;
  username: string;
  user: {
    username: string;
    full_name: string;
  };
}

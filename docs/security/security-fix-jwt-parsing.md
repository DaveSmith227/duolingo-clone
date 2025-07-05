# Security Fix: Client-Side JWT Parsing

## Issue
The current implementation parses JWT tokens on the client side to extract user roles. This is a security vulnerability because:
1. Client-side code can be modified by attackers
2. Roles should be server-authoritative
3. JWT parsing exposes implementation details

## Current Vulnerable Code
```typescript
// INSECURE - DO NOT USE
function parseRoleFromToken(accessToken: string): string {
  const parts = accessToken.split('.')
  const payload = parts[1]
  const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
  const claims = JSON.parse(decoded)
  return claims.role || 'user'
}
```

## Migration Steps

### 1. Update Backend API
Ensure the `/api/auth/me` endpoint returns user role:
```typescript
// backend/app/api/auth/auth_session.py
@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user)
):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,  // Include role in response
        "firstName": user.first_name,
        "lastName": user.last_name,
        // ... other fields
    }
```

### 2. Replace authStore.ts
```bash
# Backup old store
mv src/stores/authStore.ts src/stores/authStore.old.ts

# Use secure version
mv src/stores/authStore.secure.ts src/stores/authStore.ts
```

### 3. Update Components Using Role
Replace any component that accesses role from JWT parsing:

**Before:**
```typescript
const role = parseRoleFromToken(session.access_token)
```

**After:**
```typescript
const { user } = useAuthStore()
const role = user?.role || 'user'
```

### 4. Add Server Fetch After Login
The secure auth store automatically fetches user details after login:
```typescript
// This happens automatically in the secure store
await get().fetchUserDetails()
```

### 5. Update Role-Based Components
Components that check roles should use the store method:
```typescript
const { hasRole } = useAuthStore()

if (hasRole('admin')) {
  // Show admin UI
}
```

## Testing Checklist
- [ ] Login flow works correctly
- [ ] User role is fetched from server
- [ ] Role-based UI elements display correctly
- [ ] No JWT parsing in browser console
- [ ] Session refresh maintains user role

## Security Benefits
1. **Server Authority**: Roles come from server, not client parsing
2. **Tamper Resistant**: Users cannot modify their roles
3. **Implementation Hidden**: JWT structure not exposed to client
4. **Audit Trail**: All role checks go through server

## Additional Recommendations
1. Implement proper RBAC on backend
2. Validate permissions on every API call
3. Never trust client-provided role information
4. Log all authorization decisions
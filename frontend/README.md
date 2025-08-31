# AI Resume Review Platform - Frontend

## Architecture Overview

This is the Next.js frontend for the AI Resume Review Platform, built with TypeScript, Tailwind CSS, and React Hook Form. The frontend follows strict separation of concerns principles for maintainable, testable, and reusable code.

## 🏗️ **Critical Architecture Pattern: Separation of Concerns**

### **MUST FOLLOW: API Layer Architecture**

**✅ API Layer Responsibilities** (`src/lib/api.ts`):
- Make HTTP requests to backend
- Handle token refresh automatically  
- Transform and standardize errors into typed error classes
- Return structured `ApiResult<T>` responses
- **NEVER** handle navigation or UI logic

**✅ Auth Context Responsibilities** (`src/lib/auth-context.tsx`):
- Handle authentication state management
- Decide navigation strategy based on error types
- Provide centralized auth expiration handling
- Manage UI feedback for auth failures

**❌ FORBIDDEN: Navigation in API Layer**
```typescript
// ❌ NEVER DO THIS in api.ts
window.location.href = '/login'  // VIOLATES separation of concerns

// ✅ CORRECT: Return error types, let UI decide
throw new AuthExpiredError('Session expired')
```

### **Error Handling Flow**

```typescript
// 1. API detects 401 error
api.ts → AuthExpiredError thrown

// 2. Auth context catches error  
auth-context.tsx → handleAuthExpired()

// 3. UI layer decides action
router.push('/login')  // or show modal, or inline error
```

## 🎯 **API Usage Patterns**

### **Using API Results**
```typescript
// ✅ CORRECT: Handle ApiResult pattern
const result = await authApi.login(credentials)
if (result.success && result.data) {
  // Handle success
  setUser(result.data.user)
} else if (result.error instanceof AuthInvalidError) {
  // Handle auth errors
  setError(result.error.message)
} else if (result.error instanceof NetworkError) {
  // Handle network errors
  setError('Please check your connection')
}
```

### **Error Types Available**
- `AuthExpiredError`: Session expired, needs re-authentication
- `AuthInvalidError`: Invalid credentials, account locked, rate limited
- `NetworkError`: Connection failures, timeouts
- `Error`: General unexpected errors

## 🔐 **Authentication Patterns**

### **Using Auth Context**
```typescript
const { user, login, logout, error, handleAuthExpired } = useAuth()

// Login with proper error handling
const handleLogin = async (credentials) => {
  const success = await login(credentials)
  if (success) {
    router.push('/dashboard')
  }
  // Error is automatically set in context
}
```

### **Protected Routes**
```typescript
// ✅ Use ProtectedRoute component
<ProtectedRoute>
  <DashboardPage />
</ProtectedRoute>

// ✅ Or use withAuth HOC
export default withAuth(DashboardPage)
```

## 📁 **Project Structure**

```
src/
├── app/                    # Next.js app router pages
├── components/
│   ├── forms/             # Form components (LoginForm, etc.)
│   ├── layout/            # Layout components (Header, Container, etc.)
│   └── ui/                # Reusable UI components (Button, Input, etc.)
├── lib/
│   ├── api.ts            # ✅ Pure API layer (no navigation)
│   ├── auth-context.tsx  # ✅ Auth state + navigation logic
│   └── utils.ts          # Utility functions
└── types/
    └── index.ts          # ✅ Custom error types + interfaces
```

## 🛠️ **Development Guidelines**

### **Component Development**
1. **Follow existing patterns**: Check similar components before creating new ones
2. **Use TypeScript**: All components must have proper types
3. **Use design system**: Use components from `src/components/ui/`
4. **Handle loading states**: Show appropriate loading indicators
5. **Error boundaries**: Wrap components that might fail

### **State Management**
- **Auth state**: Use `useAuth()` hook from auth context
- **Local state**: Use `useState` for component-specific state
- **Form state**: Use React Hook Form for complex forms
- **Global state**: Extend auth context or create new contexts as needed

### **Error Handling Standards**
```typescript
// ✅ CORRECT: Component handles its own error UI
const { error, clearError } = useAuth()

if (error) {
  return <Alert type="error" onClose={clearError}>{error}</Alert>
}
```

## 🔄 **API Integration Rules**

### **Making API Calls**
```typescript
// ✅ CORRECT: Let auth context handle auth errors
const { handleAuthExpired } = useAuth()

try {
  const result = await authApi.getCurrentUser()
  if (!result.success && result.error instanceof AuthExpiredError) {
    handleAuthExpired()  // Centralized handling
    return
  }
} catch (error) {
  // Handle unexpected errors
}
```

### **Custom API Functions**
When adding new API functions, follow this pattern:
```typescript
export const myApi = {
  async getData(): Promise<ApiResult<MyData>> {
    try {
      const response = await api.get<MyData>('/my-endpoint')
      return { success: true, data: response.data }
    } catch (error) {
      if (error instanceof AuthExpiredError || /* other custom errors */) {
        return { success: false, error }
      }
      
      try {
        handleApiError(error as AxiosError)
      } catch (customError) {
        return { success: false, error: customError as Error }
      }
      
      return { success: false, error: new Error('Unexpected error occurred') }
    }
  }
}
```

## 🧪 **Testing Guidelines**

### **Unit Testing API Layer**
```typescript
// ✅ EASY: No navigation mocking needed
const result = await authApi.login(invalidCredentials)
expect(result.success).toBe(false)
expect(result.error).toBeInstanceOf(AuthInvalidError)
```

### **Testing Components**
```typescript
// ✅ EASY: Mock auth context, not navigation
const mockAuth = {
  user: null,
  login: jest.fn(),
  handleAuthExpired: jest.fn(),
  // ...
}
```

## 🚀 **Getting Started**

### **Prerequisites**
- Node.js 18+ installed
- Backend running on port 8000
- Database and Redis services running

### **Setup**
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm run test
```

### **Environment Variables**
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📋 **Development Checklist**

Before submitting any frontend PR, ensure:

- [ ] **Separation of Concerns**: No navigation logic in API layer
- [ ] **Error Handling**: Proper use of custom error types
- [ ] **TypeScript**: No `any` types, proper interfaces defined
- [ ] **Testing**: Unit tests for logic, integration tests for flows
- [ ] **Design System**: Uses existing UI components
- [ ] **Performance**: No unnecessary re-renders or API calls
- [ ] **Accessibility**: ARIA labels, keyboard navigation, proper contrast

## 🎨 **Design System**

### **Available Components**
- **Layout**: `Container`, `Grid`, `Section`, `Header`
- **Forms**: `Input`, `Button`, `LoginForm`
- **Feedback**: `Alert`, `Toast`, `Loading`
- **Structure**: `Card`, `Modal`

### **Styling Guidelines**
- Use Tailwind CSS utility classes
- Follow existing color scheme and spacing
- Ensure responsive design (mobile-first)
- Test on multiple screen sizes

## 🔍 **Debugging**

### **Common Issues**
1. **500 Errors**: Check if backend is running on port 8000
2. **CORS Errors**: Ensure frontend runs on port 3000
3. **Auth Errors**: Check browser dev tools for proper error types
4. **Token Issues**: Check localStorage for valid tokens

### **Development Tools**
- **Backend API Docs**: http://localhost:8000/docs
- **Backend Health**: http://localhost:8000/health
- **React DevTools**: Browser extension for component debugging

---

## 🎉 **Team Success Guidelines**

Following these patterns ensures:
- **Maintainable Code**: Clear separation of responsibilities
- **Easy Testing**: Pure functions without side effects
- **Flexible UX**: Components control their own behavior
- **Reusable Logic**: API layer works in any context
- **Team Velocity**: Consistent patterns reduce learning curve

**Questions?** Refer to `docs/working-agreements.md` or ask in `#dev-general` Slack channel.

---

*Last Updated: Sprint 002 - Separation of Concerns Architecture Implementation*
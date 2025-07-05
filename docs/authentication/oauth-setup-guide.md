# OAuth Provider Setup Guide

This guide provides step-by-step instructions for configuring OAuth providers in Supabase for the Duolingo Clone application.

## Prerequisites

1. Supabase project created and configured
2. Domain/redirect URLs finalized
3. Access to provider developer consoles

## Redirect URLs

Configure these redirect URLs in each provider:

- **Development**: `http://localhost:3000/auth/callback`
- **Production**: `https://yourdomain.com/auth/callback`
- **Supabase Auth**: `https://your-project-ref.supabase.co/auth/v1/callback`

## Provider Configuration

### 1. Google OAuth Setup

#### Google Cloud Console Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing project
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Configure consent screen:
   - Application name: "Duolingo Clone"
   - User support email: your-email@domain.com
   - Developer contact: your-email@domain.com
6. Create OAuth 2.0 Client ID:
   - Application type: Web application
   - Name: "Duolingo Clone Web Client"
   - Authorized JavaScript origins:
     - `http://localhost:3000` (development)
     - `https://yourdomain.com` (production)
     - `https://your-project-ref.supabase.co` (Supabase)
   - Authorized redirect URIs:
     - `http://localhost:3000/auth/callback`
     - `https://yourdomain.com/auth/callback`
     - `https://your-project-ref.supabase.co/auth/v1/callback`

#### Supabase Configuration

1. Go to Supabase Dashboard → Authentication → Providers
2. Enable Google provider
3. Enter Client ID and Client Secret from Google Console
4. Save configuration

### 2. Apple OAuth Setup

#### Apple Developer Configuration

1. Go to [Apple Developer](https://developer.apple.com/)
2. Sign in to Apple Developer account
3. Go to "Certificates, Identifiers & Profiles"
4. Create App ID:
   - Description: "Duolingo Clone"
   - Bundle ID: `com.yourcompany.duolingo-clone`
   - Enable "Sign In with Apple"
5. Create Service ID:
   - Description: "Duolingo Clone Web"
   - Identifier: `com.yourcompany.duolingo-clone.web`
   - Enable "Sign In with Apple"
   - Configure domains and redirect URLs:
     - Domains: `yourdomain.com`, `your-project-ref.supabase.co`
     - Redirect URLs: 
       - `https://yourdomain.com/auth/callback`
       - `https://your-project-ref.supabase.co/auth/v1/callback`
6. Create Private Key:
   - Register new key
   - Enable "Sign In with Apple"
   - Download .p8 file (keep secure)

#### Supabase Configuration

1. Go to Supabase Dashboard → Authentication → Providers
2. Enable Apple provider
3. Enter:
   - Client ID: Service ID identifier
   - Client Secret: Generated JWT (see Apple docs)
4. Save configuration

### 3. Facebook OAuth Setup

#### Facebook Developer Configuration

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create new app:
   - App name: "Duolingo Clone"
   - App purpose: "Business"
   - App type: "Consumer"
3. Add Facebook Login product
4. Configure Facebook Login settings:
   - Valid OAuth Redirect URIs:
     - `http://localhost:3000/auth/callback`
     - `https://yourdomain.com/auth/callback`
     - `https://your-project-ref.supabase.co/auth/v1/callback`
   - Valid Deauthorize Callback URL: `https://yourdomain.com/auth/deauthorize`
   - Valid Data Deletion Request Callback URL: `https://yourdomain.com/auth/data-deletion`
5. Go to App Settings → Basic:
   - Add App Domains: `yourdomain.com`, `your-project-ref.supabase.co`
   - Privacy Policy URL: `https://yourdomain.com/privacy`
   - Terms of Service URL: `https://yourdomain.com/terms`

#### Supabase Configuration

1. Go to Supabase Dashboard → Authentication → Providers
2. Enable Facebook provider
3. Enter App ID and App Secret from Facebook Developer Console
4. Save configuration

### 4. TikTok OAuth Setup

#### TikTok Developer Configuration

1. Go to [TikTok Developers](https://developers.tiktok.com/)
2. Create new app:
   - App name: "Duolingo Clone"
   - App description: "Language learning application"
   - Category: "Education"
3. Add Login Kit product
4. Configure redirect URLs:
   - `http://localhost:3000/auth/callback`
   - `https://yourdomain.com/auth/callback`
   - `https://your-project-ref.supabase.co/auth/v1/callback`
5. Request permissions:
   - `user.info.basic` (required)
   - `user.info.profile` (for profile information)

#### Supabase Configuration

1. Go to Supabase Dashboard → Authentication → Providers
2. Enable TikTok provider (if available) or configure as custom provider
3. Enter Client Key and Client Secret from TikTok Developer Console
4. Save configuration

## Environment Variables

After completing provider setup, update your `.env` file with the following values:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Apple OAuth
APPLE_CLIENT_ID=com.yourcompany.duolingo-clone.web
APPLE_TEAM_ID=your-apple-team-id
APPLE_KEY_ID=your-apple-key-id
APPLE_PRIVATE_KEY_PATH=path/to/apple/private/key.p8

# Facebook OAuth
FACEBOOK_APP_ID=your-facebook-app-id
FACEBOOK_APP_SECRET=your-facebook-app-secret

# TikTok OAuth
TIKTOK_CLIENT_KEY=your-tiktok-client-key
TIKTOK_CLIENT_SECRET=your-tiktok-client-secret

# OAuth Redirect URLs
FRONTEND_URL=http://localhost:3000
OAUTH_REDIRECT_URL=${FRONTEND_URL}/auth/callback
```

## Verification Steps

1. Test each provider login flow in Supabase Auth dashboard
2. Verify redirect URLs work correctly
3. Confirm user profile data is retrieved properly
4. Test logout and token refresh flows
5. Validate error handling for denied permissions

## Security Considerations

1. Keep all client secrets secure and never commit to version control
2. Use environment-specific redirect URLs
3. Implement proper CSRF protection
4. Validate all OAuth state parameters
5. Regularly rotate client secrets
6. Monitor for unauthorized OAuth applications

## Troubleshooting

### Common Issues

1. **Invalid redirect URI**: Ensure exact match between configured and actual URLs
2. **Invalid client credentials**: Verify client ID and secret are correctly copied
3. **Scope permissions denied**: Check if requested scopes are approved by provider
4. **Domain verification failed**: Ensure domains are properly verified in provider console

### Debug Steps

1. Check Supabase Auth logs for detailed error messages
2. Verify provider developer console settings
3. Test with provider's OAuth playground tools
4. Check network requests in browser developer tools
5. Validate JWT tokens using jwt.io

## Production Deployment

Before going live:

1. Switch to production OAuth credentials
2. Update redirect URLs to production domains
3. Enable SSL/HTTPS for all endpoints
4. Configure proper CORS settings
5. Set up monitoring and alerting
6. Test all provider flows in production environment
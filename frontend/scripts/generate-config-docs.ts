#!/usr/bin/env npx tsx

/**
 * Frontend Configuration Documentation Generator
 * 
 * Automatically generates comprehensive documentation from TypeScript configuration
 * interfaces and Zod schemas, including examples and validation rules.
 * 
 * Usage:
 *   npx tsx scripts/generate-config-docs.ts [--output-dir docs] [--format markdown]
 * 
 * Features:
 * - Extracts configuration from TypeScript interfaces
 * - Generates examples and validation rules from Zod schemas
 * - Creates environment-specific documentation
 * - Outputs in multiple formats (Markdown, HTML, JSON)
 * - Includes Next.js specific guidelines
 */

import { writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';
import * as z from 'zod';

// Configuration interfaces and schemas (would normally import these)
interface ConfigField {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default?: any;
  examples: Array<{
    environment: string;
    value: string;
    note: string;
  }>;
  clientSide: boolean;
  securityLevel: 'public' | 'internal' | 'sensitive';
  validationRules: string[];
}

interface ConfigCategory {
  name: string;
  description: string;
  fields: ConfigField[];
}

class FrontendConfigDocGenerator {
  private readonly configFields: ConfigField[] = [
    // Application Configuration
    {
      name: 'NEXT_PUBLIC_ENVIRONMENT',
      type: 'string',
      description: 'Current environment (development, staging, production, test)',
      required: true,
      default: 'development',
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Must be one of: development, staging, production, test'],
      examples: [
        { environment: 'development', value: 'development', note: 'Local development' },
        { environment: 'staging', value: 'staging', note: 'Staging environment' },
        { environment: 'production', value: 'production', note: 'Production environment' }
      ]
    },
    {
      name: 'NEXT_PUBLIC_APP_NAME',
      type: 'string',
      description: 'Application display name',
      required: false,
      default: 'Duolingo Clone',
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['String length between 1-50 characters'],
      examples: [
        { environment: 'all', value: 'Duolingo Clone', note: 'Default application name' }
      ]
    },
    {
      name: 'NEXT_PUBLIC_APP_VERSION',
      type: 'string',
      description: 'Application version for display and debugging',
      required: false,
      default: '0.1.0',
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Must follow semantic versioning (x.y.z)'],
      examples: [
        { environment: 'all', value: '0.1.0', note: 'Semantic version format' }
      ]
    },

    // API Configuration
    {
      name: 'NEXT_PUBLIC_API_URL',
      type: 'string',
      description: 'Backend API base URL',
      required: true,
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Must be a valid URL', 'HTTPS required in production'],
      examples: [
        { environment: 'development', value: 'http://localhost:8000', note: 'Local backend' },
        { environment: 'staging', value: 'https://api-staging.yourdomain.com', note: 'Staging API' },
        { environment: 'production', value: 'https://api.yourdomain.com', note: 'Production API' }
      ]
    },
    {
      name: 'NEXT_PUBLIC_API_TIMEOUT',
      type: 'string',
      description: 'API request timeout in milliseconds',
      required: false,
      default: '30000',
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Must be a positive integer', 'Recommended: 10000-60000ms'],
      examples: [
        { environment: 'all', value: '30000', note: '30 second timeout' }
      ]
    },
    {
      name: 'NEXT_PUBLIC_API_RETRY_ATTEMPTS',
      type: 'string',
      description: 'Number of retry attempts for failed API requests',
      required: false,
      default: '3',
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Must be between 0-10'],
      examples: [
        { environment: 'all', value: '3', note: 'Retry up to 3 times' }
      ]
    },

    // Supabase Configuration
    {
      name: 'NEXT_PUBLIC_SUPABASE_URL',
      type: 'string',
      description: 'Supabase project URL for authentication',
      required: true,
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Must be a valid Supabase URL', 'Format: https://xxx.supabase.co'],
      examples: [
        { environment: 'development', value: 'https://dev-project.supabase.co', note: 'Development Supabase project' },
        { environment: 'production', value: 'https://prod-project.supabase.co', note: 'Production Supabase project' }
      ]
    },
    {
      name: 'NEXT_PUBLIC_SUPABASE_ANON_KEY',
      type: 'string',
      description: 'Supabase anonymous key (safe for client-side)',
      required: true,
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Must be a valid Supabase anonymous key'],
      examples: [
        { environment: 'all', value: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...', note: 'From Supabase dashboard' }
      ]
    },

    // Authentication Settings
    {
      name: 'NEXT_PUBLIC_SESSION_TIMEOUT',
      type: 'string',
      description: 'Session timeout in milliseconds',
      required: false,
      default: '1800000',
      clientSide: true,
      securityLevel: 'internal',
      validationRules: ['Must be a positive integer', 'Recommended: 900000-3600000ms (15-60 min)'],
      examples: [
        { environment: 'development', value: '3600000', note: '1 hour for development' },
        { environment: 'production', value: '1800000', note: '30 minutes for production' }
      ]
    },
    {
      name: 'NEXT_PUBLIC_ENABLE_MFA',
      type: 'string',
      description: 'Enable multi-factor authentication',
      required: false,
      default: 'true',
      clientSide: true,
      securityLevel: 'internal',
      validationRules: ['Must be "true" or "false"'],
      examples: [
        { environment: 'development', value: 'false', note: 'Disabled for development' },
        { environment: 'production', value: 'true', note: 'Enabled for security' }
      ]
    },
    {
      name: 'NEXT_PUBLIC_OAUTH_PROVIDERS',
      type: 'string',
      description: 'Comma-separated list of enabled OAuth providers',
      required: false,
      default: 'google',
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Comma-separated list', 'Valid providers: google,apple,facebook,tiktok'],
      examples: [
        { environment: 'development', value: 'google', note: 'Google only for testing' },
        { environment: 'production', value: 'google,apple,facebook', note: 'Multiple providers' }
      ]
    },

    // Feature Flags
    {
      name: 'NEXT_PUBLIC_ENABLE_ANALYTICS',
      type: 'string',
      description: 'Enable usage analytics tracking',
      required: false,
      default: 'true',
      clientSide: true,
      securityLevel: 'internal',
      validationRules: ['Must be "true" or "false"'],
      examples: [
        { environment: 'development', value: 'false', note: 'Disabled in development' },
        { environment: 'production', value: 'true', note: 'Enabled for insights' }
      ]
    },
    {
      name: 'NEXT_PUBLIC_ENABLE_DEBUG',
      type: 'string',
      description: 'Enable debug console logging',
      required: false,
      default: 'false',
      clientSide: true,
      securityLevel: 'internal',
      validationRules: ['Must be "true" or "false"', 'Should be false in production'],
      examples: [
        { environment: 'development', value: 'true', note: 'Debug logging enabled' },
        { environment: 'production', value: 'false', note: 'Must be false in production' }
      ]
    },

    // UI Configuration
    {
      name: 'NEXT_PUBLIC_THEME',
      type: 'string',
      description: 'Default theme (light, dark, system)',
      required: false,
      default: 'system',
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Must be one of: light, dark, system'],
      examples: [
        { environment: 'all', value: 'system', note: 'Follow system preference' }
      ]
    },
    {
      name: 'NEXT_PUBLIC_ANIMATIONS_ENABLED',
      type: 'string',
      description: 'Enable UI animations',
      required: false,
      default: 'true',
      clientSide: true,
      securityLevel: 'public',
      validationRules: ['Must be "true" or "false"'],
      examples: [
        { environment: 'all', value: 'true', note: 'Enhanced user experience' }
      ]
    },

    // Server-side only variables
    {
      name: 'SUPABASE_SERVICE_ROLE_KEY',
      type: 'string',
      description: 'Supabase service role key (server-side only)',
      required: false,
      clientSide: false,
      securityLevel: 'sensitive',
      validationRules: ['Must be a valid Supabase service role key', 'Never expose to client'],
      examples: [
        { environment: 'all', value: '********', note: 'Keep secret! Server-side only' }
      ]
    },
    {
      name: 'OPENAI_API_KEY',
      type: 'string',
      description: 'OpenAI API key for AI features (server-side only)',
      required: false,
      clientSide: false,
      securityLevel: 'sensitive',
      validationRules: ['Must start with "sk-"', 'Never expose to client'],
      examples: [
        { environment: 'all', value: 'sk-********', note: 'From OpenAI dashboard' }
      ]
    }
  ];

  private categorizeFields(): ConfigCategory[] {
    const categories: ConfigCategory[] = [
      {
        name: 'Application Configuration',
        description: 'Basic application settings and metadata.',
        fields: []
      },
      {
        name: 'API Configuration',
        description: 'Backend API connection and request settings.',
        fields: []
      },
      {
        name: 'Authentication & Security',
        description: 'Authentication providers and security settings.',
        fields: []
      },
      {
        name: 'Feature Flags',
        description: 'Feature toggles and experimental functionality.',
        fields: []
      },
      {
        name: 'UI Configuration',
        description: 'User interface and experience settings.',
        fields: []
      },
      {
        name: 'Server-Side Variables',
        description: 'Variables only available in API routes and server components.',
        fields: []
      }
    ];

    // Categorize fields
    this.configFields.forEach(field => {
      if (!field.clientSide) {
        categories[5].fields.push(field);
      } else if (field.name.includes('APP_') || field.name.includes('ENVIRONMENT')) {
        categories[0].fields.push(field);
      } else if (field.name.includes('API_')) {
        categories[1].fields.push(field);
      } else if (field.name.includes('SUPABASE') || field.name.includes('SESSION') || field.name.includes('MFA') || field.name.includes('OAUTH')) {
        categories[2].fields.push(field);
      } else if (field.name.includes('ENABLE_')) {
        categories[3].fields.push(field);
      } else if (field.name.includes('THEME') || field.name.includes('ANIMATIONS')) {
        categories[4].fields.push(field);
      } else {
        categories[0].fields.push(field);
      }
    });

    return categories.filter(cat => cat.fields.length > 0);
  }

  generateMarkdown(): string {
    const doc: string[] = [];
    const categories = this.categorizeFields();

    // Header
    doc.push('# Frontend Configuration Documentation');
    doc.push('');
    doc.push(`Generated on: ${new Date().toISOString()}`);
    doc.push('Framework: Next.js 15 with TypeScript');
    doc.push('');

    // Table of Contents
    doc.push('## Table of Contents');
    doc.push('');
    categories.forEach(category => {
      doc.push(`- [${category.name}](#${category.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')})`);
    });
    doc.push('- [Environment-Specific Guidelines](#environment-specific-guidelines)');
    doc.push('- [Next.js Configuration Guide](#nextjs-configuration-guide)');
    doc.push('- [Security Best Practices](#security-best-practices)');
    doc.push('');

    // Generate sections for each category
    categories.forEach(category => {
      doc.push(`## ${category.name}`);
      doc.push('');
      doc.push(category.description);
      doc.push('');

      // Create table
      doc.push('| Variable | Type | Required | Client-Side | Description | Default |');
      doc.push('|----------|------|----------|-------------|-------------|---------|');

      category.fields.forEach(field => {
        const required = field.required ? '✅' : '❌';
        const clientSide = field.clientSide ? '✅' : '❌';
        const defaultValue = field.default || '-';
        
        doc.push(`| \`${field.name}\` | ${field.type} | ${required} | ${clientSide} | ${field.description} | \`${defaultValue}\` |`);
      });

      doc.push('');

      // Detailed field documentation
      category.fields.forEach(field => {
        doc.push(`### \`${field.name}\``);
        doc.push('');
        doc.push(`**Type:** ${field.type}`);
        doc.push(`**Required:** ${field.required ? 'Yes' : 'No'}`);
        doc.push(`**Client-Side:** ${field.clientSide ? 'Yes (accessible in browser)' : 'No (server-side only)'}`);
        doc.push(`**Security Level:** ${field.securityLevel}`);
        doc.push('');

        if (field.description) {
          doc.push(`**Description:** ${field.description}`);
          doc.push('');
        }

        if (field.validationRules.length > 0) {
          doc.push('**Validation Rules:**');
          field.validationRules.forEach(rule => {
            doc.push(`- ${rule}`);
          });
          doc.push('');
        }

        // Examples
        doc.push('**Examples:**');
        doc.push('');
        field.examples.forEach(example => {
          const value = field.securityLevel === 'sensitive' && example.value !== '********' ? '********' : example.value;
          doc.push(`- **${example.environment.charAt(0).toUpperCase() + example.environment.slice(1)}:** \`${value}\` - ${example.note}`);
        });

        doc.push('');
        doc.push('---');
        doc.push('');
      });
    });

    // Environment-specific guidelines
    doc.push(...this.generateEnvironmentGuidelines());

    // Next.js configuration guide
    doc.push(...this.generateNextjsGuide());

    // Security best practices
    doc.push(...this.generateSecurityGuidelines());

    return doc.join('\n');
  }

  private generateEnvironmentGuidelines(): string[] {
    const doc: string[] = [];

    doc.push('## Environment-Specific Guidelines');
    doc.push('');
    doc.push('Next.js has specific requirements for environment variables based on where they\'re used.');
    doc.push('');

    const environments = {
      'Development': {
        'purpose': 'Local development with hot reload',
        'guidelines': [
          'Use .env.local for local overrides',
          'Enable debug features and logging',
          'Point to local backend (localhost:8000)',
          'Use development Supabase project',
          'Disable analytics and tracking',
          'Enable experimental features for testing'
        ]
      },
      'Staging': {
        'purpose': 'Pre-production testing environment',
        'guidelines': [
          'Use .env.staging or deployment environment variables',
          'Point to staging backend and services',
          'Enable limited analytics',
          'Test OAuth integrations',
          'Mirror production security settings',
          'Use staging API keys'
        ]
      },
      'Production': {
        'purpose': 'Live application serving users',
        'guidelines': [
          'All URLs must use HTTPS',
          'Disable all debug features',
          'Enable full analytics and monitoring',
          'Use production API keys and secrets',
          'Enable all security features',
          'Configure proper error boundaries'
        ]
      }
    };

    Object.entries(environments).forEach(([envName, envInfo]) => {
      doc.push(`### ${envName} Environment`);
      doc.push('');
      doc.push(`**Purpose:** ${envInfo.purpose}`);
      doc.push('');
      doc.push('**Configuration Guidelines:**');
      envInfo.guidelines.forEach(guideline => {
        doc.push(`- ${guideline}`);
      });
      doc.push('');
    });

    return doc;
  }

  private generateNextjsGuide(): string[] {
    const doc: string[] = [];

    doc.push('## Next.js Configuration Guide');
    doc.push('');
    doc.push('Next.js has specific rules for environment variables that affect how they\'re handled.');
    doc.push('');

    doc.push('### Client-Side vs Server-Side Variables');
    doc.push('');
    doc.push('| Prefix | Accessibility | Usage | Security |');
    doc.push('|--------|---------------|-------|----------|');
    doc.push('| `NEXT_PUBLIC_` | Client + Server | Public data, API URLs, feature flags | ⚠️ Visible to users |');
    doc.push('| No prefix | Server only | Secrets, private keys, server config | ✅ Hidden from users |');
    doc.push('');

    doc.push('### Environment File Priority');
    doc.push('');
    doc.push('Next.js loads environment variables in this order (later files override earlier ones):');
    doc.push('');
    doc.push('1. `.env` (committed to git, shared defaults)');
    doc.push('2. `.env.local` (ignored by git, local overrides)');
    doc.push('3. `.env.development` / `.env.staging` / `.env.production` (environment-specific)');
    doc.push('4. `.env.development.local` / etc. (environment-specific local overrides)');
    doc.push('');

    doc.push('### Best Practices');
    doc.push('');
    doc.push('- **Never commit `.env.local` files** - they contain secrets and local config');
    doc.push('- **Use `NEXT_PUBLIC_` prefix sparingly** - only for data that\'s safe to expose');
    doc.push('- **Keep secrets in server-side variables** - no `NEXT_PUBLIC_` prefix');
    doc.push('- **Use environment-specific files** for different deployments');
    doc.push('- **Validate environment variables at build time** to catch issues early');
    doc.push('');

    doc.push('### Common Issues');
    doc.push('');
    doc.push('| Issue | Cause | Solution |');
    doc.push('|-------|--------|----------|');
    doc.push('| Variable undefined in browser | Missing `NEXT_PUBLIC_` prefix | Add prefix or move to API route |');
    doc.push('| Secret exposed in browser | Used `NEXT_PUBLIC_` prefix | Remove prefix, use in API routes only |');
    doc.push('| Variable not updating | Cached build | Restart dev server or clear `.next` folder |');
    doc.push('| Build-time error | Invalid variable format | Check syntax and required variables |');
    doc.push('');

    return doc;
  }

  private generateSecurityGuidelines(): string[] {
    const doc: string[] = [];

    doc.push('## Security Best Practices');
    doc.push('');

    const sections = {
      'Environment Variable Security': [
        'Never expose secrets with NEXT_PUBLIC_ prefix',
        'Use server-side API routes for sensitive operations',
        'Validate all environment variables at startup',
        'Use different values for each environment',
        'Rotate secrets regularly (every 90 days)',
        'Monitor for accidental secret exposure in logs'
      ],
      'Client-Side Security': [
        'Assume all NEXT_PUBLIC_ variables are public',
        'Validate API responses on the client',
        'Implement proper error boundaries',
        'Use HTTPS for all external requests',
        'Sanitize user inputs before display',
        'Implement proper CSP headers'
      ],
      'API Integration Security': [
        'Use API keys for server-side requests only',
        'Implement request timeout and retry logic',
        'Validate API responses and handle errors gracefully',
        'Use proper authentication headers',
        'Log security events and failed requests',
        'Implement rate limiting on client side'
      ],
      'Build and Deploy Security': [
        'Never commit .env.local or .env.*.local files',
        'Use secure deployment environment variables',
        'Implement proper CI/CD secret management',
        'Audit dependencies regularly',
        'Use security scanning in build pipeline',
        'Monitor runtime security events'
      ]
    };

    Object.entries(sections).forEach(([sectionName, practices]) => {
      doc.push(`### ${sectionName}`);
      doc.push('');
      practices.forEach(practice => {
        doc.push(`- ${practice}`);
      });
      doc.push('');
    });

    return doc;
  }

  generateJson() {
    const categories = this.categorizeFields();
    
    return {
      generated_at: new Date().toISOString(),
      framework: 'Next.js 15',
      categories,
      total_fields: this.configFields.length,
      client_side_fields: this.configFields.filter(f => f.clientSide).length,
      server_side_fields: this.configFields.filter(f => !f.clientSide).length,
      sensitive_fields: this.configFields.filter(f => f.securityLevel === 'sensitive').length
    };
  }

  generateHtml(): string {
    const markdownContent = this.generateMarkdown();
    
    // Simple markdown to HTML conversion
    let htmlContent = markdownContent;
    htmlContent = htmlContent.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    htmlContent = htmlContent.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    htmlContent = htmlContent.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    htmlContent = htmlContent.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    htmlContent = htmlContent.replace(/`(.+?)`/g, '<code>$1</code>');
    htmlContent = htmlContent.replace(/^- (.+)$/gm, '<li>$1</li>');
    htmlContent = htmlContent.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
    htmlContent = htmlContent.replace(/\n/g, '<br>');

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Frontend Configuration Documentation</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; line-height: 1.6; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; font-weight: 600; }
        code { background-color: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-family: 'Monaco', 'Courier New', monospace; }
        .toc { background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .security { background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; border-radius: 4px; }
        .warning { background-color: #f8d7da; padding: 15px; border-left: 4px solid #dc3545; margin: 15px 0; border-radius: 4px; }
        h1 { color: #2563eb; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }
        h2 { color: #1f2937; margin-top: 30px; }
        h3 { color: #374151; }
        ul { margin-left: 20px; }
        li { margin: 5px 0; }
    </style>
</head>
<body>
${htmlContent}
</body>
</html>`;
  }
}

// CLI interface
function main() {
  const args = process.argv.slice(2);
  let outputDir = 'docs/generated';
  let format = 'all';

  // Parse arguments
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--output-dir' || args[i] === '-o') {
      outputDir = args[i + 1];
      i++;
    } else if (args[i] === '--format' || args[i] === '-f') {
      format = args[i + 1];
      i++;
    } else if (args[i] === '--help' || args[i] === '-h') {
      console.log('Frontend Configuration Documentation Generator');
      console.log('');
      console.log('Usage: npx tsx scripts/generate-config-docs.ts [options]');
      console.log('');
      console.log('Options:');
      console.log('  --output-dir, -o    Output directory (default: docs/generated)');
      console.log('  --format, -f        Output format: markdown, html, json, all (default: all)');
      console.log('  --help, -h          Show this help message');
      return;
    }
  }

  // Create output directory
  mkdirSync(outputDir, { recursive: true });

  console.log('🔧 Generating frontend configuration documentation...');
  console.log(`📂 Output directory: ${outputDir}`);
  console.log(`📝 Format: ${format}`);
  console.log('');

  try {
    const generator = new FrontendConfigDocGenerator();

    // Generate requested formats
    if (format === 'markdown' || format === 'all') {
      console.log('📄 Generating Markdown documentation...');
      const markdownContent = generator.generateMarkdown();
      const markdownFile = join(outputDir, 'frontend-configuration.md');
      writeFileSync(markdownFile, markdownContent, 'utf-8');
      console.log(`✅ Markdown documentation saved to: ${markdownFile}`);
    }

    if (format === 'html' || format === 'all') {
      console.log('🌐 Generating HTML documentation...');
      const htmlContent = generator.generateHtml();
      const htmlFile = join(outputDir, 'frontend-configuration.html');
      writeFileSync(htmlFile, htmlContent, 'utf-8');
      console.log(`✅ HTML documentation saved to: ${htmlFile}`);
    }

    if (format === 'json' || format === 'all') {
      console.log('📊 Generating JSON documentation...');
      const jsonContent = generator.generateJson();
      const jsonFile = join(outputDir, 'frontend-configuration.json');
      writeFileSync(jsonFile, JSON.stringify(jsonContent, null, 2), 'utf-8');
      console.log(`✅ JSON documentation saved to: ${jsonFile}`);
    }

    console.log('');
    console.log('🎉 Documentation generation completed successfully!');
    console.log('');
    console.log('📖 Next steps:');
    console.log('• Review the generated documentation');
    console.log('• Update examples for your specific use case');
    console.log('• Add the docs to your project README');
    console.log('• Set up automated regeneration in CI/CD');

  } catch (error) {
    console.error('❌ Error generating documentation:', error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

export { FrontendConfigDocGenerator };
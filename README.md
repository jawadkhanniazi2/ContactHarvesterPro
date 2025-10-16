# Free Email Scraper Tool

A modern, free, and unlimited email scraper tool built with Next.js and React. Extract email addresses, phone numbers, and social media links from any website without any registration or usage limits.

## 🚀 Features

- **100% Free** - No registration, no credits, no limits
- **Unlimited Usage** - Scrape as many websites as you want
- **Modern UI** - Beautiful, responsive interface built with Tailwind CSS
- **Fast & Efficient** - Powered by Puppeteer for reliable web scraping
- **Multiple Data Types** - Extract emails, phone numbers, and social media links
- **Export Results** - Download results as CSV files
- **Contact Page Detection** - Automatically finds and scrapes contact pages
- **Cloudflare Email Protection** - Decodes protected email addresses
- **Mobile Friendly** - Works perfectly on all devices

## 🛠️ Tech Stack

- **Frontend**: Next.js 14, React 18, TypeScript
- **Styling**: Tailwind CSS
- **Scraping**: Puppeteer Core
- **Parsing**: Cheerio
- **Deployment**: Vercel
- **Icons**: Lucide React

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd email-scraper-tool
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📦 Deployment

### Deploy to Vercel

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Deploy with one click

The app is optimized for Vercel deployment with proper Puppeteer configuration.

### Environment Variables

Create a `.env.local` file:

```env
PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
NODE_ENV=production
```

## 🎯 Usage

1. **Enter URLs**: Add one or more website URLs (one per line)
2. **Start Scraping**: Click the "Start Scraping" button
3. **View Results**: See extracted emails, phones, and social media links
4. **Download Data**: Export results as CSV file

### Supported URL Formats

- `https://example.com`
- `http://example.com`
- `example.com` (automatically adds https://)

## 🔧 API Reference

### POST /api/scrape

Scrape contact information from websites.

**Request Body:**
```json
{
  "urls": ["https://example.com", "https://another-site.com"]
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "url": "https://example.com",
      "domain": "example.com",
      "emails": ["contact@example.com"],
      "phones": ["+1-555-123-4567"],
      "social_media": {
        "facebook": "https://facebook.com/example",
        "twitter": "https://twitter.com/example"
      },
      "status": "success"
    }
  ],
  "summary": {
    "total_urls": 1,
    "successful": 1,
    "total_emails": 1,
    "total_phones": 1
  }
}
```

## 🎨 Customization

### Styling

The app uses Tailwind CSS. Customize colors and styles in:
- `tailwind.config.js` - Theme configuration
- `app/globals.css` - Global styles and custom components

### Scraping Logic

Modify scraping behavior in:
- `app/api/scrape/route.ts` - Main scraping logic
- Add new extraction patterns for different data types

## 🔒 Privacy & Ethics

- **Respect robots.txt**: Always check website policies
- **Rate Limiting**: Built-in delays prevent server overload
- **No Data Storage**: Results are not stored on servers
- **Client-Side Processing**: Data stays in your browser

## 🐛 Troubleshooting

### Common Issues

1. **Puppeteer Errors**: Ensure proper Chromium configuration for your platform
2. **Timeout Issues**: Some websites may take longer to load
3. **Blocked Requests**: Some sites block automated requests

### Performance Tips

- Limit concurrent requests (max 10 URLs per batch)
- Use specific URLs rather than homepage for better results
- Check website's contact or about pages manually first

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚠️ Disclaimer

This tool is for educational and legitimate business purposes only. Always respect website terms of service and applicable laws. Users are responsible for ensuring their use complies with all relevant regulations.

## 🆘 Support

If you encounter any issues or have questions, please open an issue on GitHub.

---

**Made with ❤️ for the developer community**

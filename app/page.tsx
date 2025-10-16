'use client'

import { useState } from 'react'
import { Search, Mail, Download, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import axios from 'axios'

interface ScrapedData {
  url: string
  domain: string
  emails: string[]
  status: string
}

export default function Home() {
  const [urls, setUrls] = useState('')
  const [results, setResults] = useState<ScrapedData[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(0)
  const [completedSites, setCompletedSites] = useState(0)
  const [totalSites, setTotalSites] = useState(0)

  const handleScrape = async () => {
    if (!urls.trim()) {
      setError('Please enter at least one URL')
      return
    }

    setIsLoading(true)
    setError('')
    setResults([])
    setProgress(0)
    setCompletedSites(0)

    try {
      const urlList = urls.split('\n').filter(url => url.trim())
      setTotalSites(urlList.length)
      
      // Simulate progressive scraping by processing URLs in batches
      const batchSize = 1
      const allResults: ScrapedData[] = []
      
      for (let i = 0; i < urlList.length; i += batchSize) {
        const batch = urlList.slice(i, i + batchSize)
        
        const response = await axios.post('/api/scrape', {
          urls: batch
        })

        if (response.data.success) {
          allResults.push(...response.data.results)
          setResults([...allResults])
          
          // Update progress
          const completed = i + batch.length
          setCompletedSites(completed)
          setProgress(Math.round((completed / urlList.length) * 100))
        } else {
          setError(response.data.error || 'An error occurred while scraping')
          break
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to scrape URLs. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const downloadResults = () => {
    if (results.length === 0) return

    const csvContent = [
      ['URL', 'Domain', 'Emails', 'Status'].join(','),
      ...results.map(result => [
        result.url,
        result.domain,
        result.emails.join('; '),
        result.status
      ].map(field => `"${field}"`).join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `email-scraper-results-${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }

  const totalEmails = results.reduce((sum, result) => sum + result.emails.length, 0)
  const successfulScrapes = results.filter(result => result.status === 'success').length

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-6xl font-bold text-gradient mb-4">
          Free Email Scraper Tool
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
          Extract email addresses from any website with advanced detection capabilities. 
          Completely free, unlimited usage, no signup required.
        </p>
        
        <div className="flex flex-wrap justify-center gap-6 text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>100% Free</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>Unlimited Usage</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>No Registration</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>Instant Results</span>
          </div>
        </div>
      </div>

      {/* Main Tool */}
      <div className="card mb-8">
        <div className="mb-6">
          <label htmlFor="urls" className="block text-sm font-medium text-gray-700 mb-2">
            Enter URLs to scrape (one per line)
          </label>
          <textarea
            id="urls"
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
            placeholder="https://example.com&#10;https://another-site.com&#10;company-website.com"
            className="input-field h-32 resize-none"
            disabled={isLoading}
          />
          <p className="text-sm text-gray-500 mt-2">
            You can enter multiple URLs, one per line. HTTP/HTTPS prefix is optional.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <span className="text-red-700">{error}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-4">
          <button
            onClick={handleScrape}
            disabled={isLoading || !urls.trim()}
            className="btn-primary flex items-center justify-center gap-2 flex-1"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <div className="flex flex-col items-center">
                  <span>Scraping... {progress}%</span>
                  {totalSites > 0 && (
                    <span className="text-xs opacity-75">
                      {completedSites} of {totalSites} sites completed
                    </span>
                  )}
                </div>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Start Scraping
              </>
            )}
          </button>
          
          {results.length > 0 && (
            <button
              onClick={downloadResults}
              className="btn-secondary flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              Download CSV
            </button>
          )}
        </div>

        {/* Progress Bar */}
        {isLoading && totalSites > 0 && (
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-sm text-gray-600">
              <span>Progress: {completedSites} / {totalSites} sites</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-indigo-500 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Results Summary */}
      {results.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="relative overflow-hidden bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl p-6 text-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
            <div className="absolute top-0 right-0 w-20 h-20 bg-white opacity-10 rounded-full -mr-10 -mt-10"></div>
            <div className="relative">
              <div className="text-3xl font-bold mb-2">🌐 {results.length}</div>
              <div className="text-purple-100 font-medium">URLs Processed</div>
            </div>
          </div>
          <div className="relative overflow-hidden bg-gradient-to-br from-emerald-500 to-green-600 rounded-xl p-6 text-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
            <div className="absolute top-0 right-0 w-20 h-20 bg-white opacity-10 rounded-full -mr-10 -mt-10"></div>
            <div className="relative">
              <div className="text-3xl font-bold mb-2">✅ {successfulScrapes}</div>
              <div className="text-emerald-100 font-medium">Successful Scrapes</div>
            </div>
          </div>
          <div className="relative overflow-hidden bg-gradient-to-br from-blue-500 to-cyan-600 rounded-xl p-6 text-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
            <div className="absolute top-0 right-0 w-20 h-20 bg-white opacity-10 rounded-full -mr-10 -mt-10"></div>
            <div className="relative">
              <div className="text-3xl font-bold mb-2">📧 {totalEmails}</div>
              <div className="text-blue-100 font-medium">Emails Found</div>
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Results Section */}
      {results.length > 0 && (
        <div className="space-y-6">
          <div className="text-center">
            <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-2">
              🎉 Scraping Results
            </h2>
            <p className="text-gray-600">Here are the emails we found for you!</p>
          </div>
          
          {/* Enhanced Header Section */}
          <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 rounded-t-xl p-6 shadow-xl">
            <div className="grid grid-cols-2 gap-4 text-white">
              <div className="flex items-center gap-3">
                <div className="bg-white bg-opacity-20 p-2 rounded-full">
                  <div className="w-4 h-4 bg-white rounded-full animate-pulse"></div>
                </div>
                <span className="text-lg font-bold tracking-wide">🌐 Website</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="bg-white bg-opacity-20 p-2 rounded-full">
                  <Mail className="w-4 h-4 text-white" />
                </div>
                <span className="text-lg font-bold tracking-wide">📧 Email Addresses</span>
              </div>
            </div>
          </div>

          {/* Enhanced Results Container */}
          <div className="bg-white rounded-b-xl shadow-xl overflow-hidden border-2 border-gray-100">
            {results.map((result, index) => (
              <div key={index} className={`grid grid-cols-2 gap-6 p-6 border-b-2 border-gray-50 hover:bg-gradient-to-r hover:from-blue-50 hover:via-purple-50 hover:to-pink-50 transition-all duration-500 transform hover:scale-[1.02] ${index === results.length - 1 ? 'border-b-0' : ''}`}>
                
                {/* Website Column - Enhanced */}
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-4 h-4 rounded-full shadow-lg ${result.status === 'success' ? 'bg-gradient-to-r from-green-400 to-emerald-500 animate-pulse' : 'bg-gradient-to-r from-red-400 to-pink-500'}`}></div>
                    <h3 className="font-bold text-xl text-gray-800 bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">{result.domain}</h3>
                  </div>
                  <div className="bg-gradient-to-r from-gray-50 to-blue-50 px-4 py-3 rounded-xl border border-gray-200">
                    <p className="text-sm text-gray-600 break-all font-mono">
                      {result.url}
                    </p>
                  </div>
                  <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold shadow-md ${
                    result.status === 'success' 
                      ? 'bg-gradient-to-r from-green-100 to-emerald-100 text-green-700 border-2 border-green-200' 
                      : 'bg-gradient-to-r from-red-100 to-pink-100 text-red-700 border-2 border-red-200'
                  }`}>
                    {result.status === 'success' ? '🎉 Success' : '💥 Failed'}
                  </span>
                </div>

                {/* Email Column - Enhanced */}
                <div className="space-y-3">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 p-2 rounded-full shadow-lg">
                      <Mail className="w-4 h-4 text-white" />
                    </div>
                    <span className="font-bold text-lg text-gray-700 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                      {result.emails.length} Email{result.emails.length !== 1 ? 's' : ''} Found
                    </span>
                  </div>
                  
                  <div className="space-y-3 max-h-40 overflow-y-auto custom-scrollbar">
                    {result.emails.length > 0 ? (
                      result.emails.map((email, i) => (
                        <div key={i} className="group">
                          <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-cyan-50 border-2 border-emerald-200 px-4 py-3 rounded-xl text-sm font-semibold text-emerald-800 hover:from-emerald-100 hover:via-teal-100 hover:to-cyan-100 hover:border-emerald-300 transition-all duration-300 cursor-pointer transform hover:scale-105 shadow-sm hover:shadow-md">
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-2">
                                <span className="text-lg">📧</span>
                                <span className="font-mono">{email}</span>
                              </span>
                              <div className="opacity-0 group-hover:opacity-100 transition-all duration-300">
                                <span className="text-xs text-emerald-600 bg-emerald-100 px-2 py-1 rounded-full">Click to copy</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-8">
                        <div className="bg-gradient-to-r from-gray-100 to-gray-200 rounded-xl p-6">
                          <div className="text-gray-400 text-sm">
                            <div className="text-4xl mb-3">📭</div>
                            <div className="font-semibold">No emails found</div>
                            <div className="text-xs mt-1">Try checking the contact page</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-16 text-center text-gray-500 text-sm">
        <p>© 2024 Free Email Scraper Tool. Use responsibly and respect website terms of service.</p>
      </footer>
    </div>
  )
}
# CafeHop

A serverless application for managing and viewing cafe photos with AWS Lambda and S3 integration. The project includes authentication, S3 presigned URL generation for photo uploads, and integration with Google Maps API for cafe location data.

## Project Structure

```
cafeHop/
├── function/
│   ├── generate_s3_url_lambda_function.py  # Lambda function to generate S3 presigned URLs
│   ├── simple_auth_lambda_function.py      # JWT-based authentication Lambda function
│   └── requirements.txt                    # Python dependencies for Lambda functions
├── template.yml                            # AWS SAM template for deployment
├── 1-create-bucket.sh                      # Script to create S3 bucket for deployment artifacts
├── 2-build-layer.sh                        # Script to build Lambda layer with dependencies
├── 3-deploy.sh                             # Script to package and deploy the application
├── 4-invoke.sh                             # Script to test/invoke Lambda functions
├── 5-cleanup.sh                            # Script to clean up AWS resources
├── index.html                              # Main gallery page for viewing cafe photos
├── add.html                                # Page for adding new cafe photos
├── map.html                                # Interactive map view of cafes
└── requirements.txt                        # Local development dependencies
```

## Features

- **Photo Upload**: Generate presigned S3 URLs for secure photo uploads
- **Authentication**: Simple JWT-based authentication for protected endpoints
- **Image Metadata**: Extract GPS coordinates from image EXIF data
- **CORS Support**: Configured for GitHub Pages deployment

## Lambda Functions

### 1. Generate S3 URL Function (`generate_s3_url_lambda_function.py`)
- Generates presigned S3 URLs for uploading cafe photos
- Stores metadata (cafe name, rating, notes, coordinates) with images
- Handles CORS for cross-origin requests
- Generates filenames based on cafe name and rating

### 2. Simple Auth Function (`simple_auth_lambda_function.py`)
- Validates password and generates JWT tokens
- Tokens are valid for 5 minutes
- Simple password-based authentication

### 3. Utils Module (`utils.py`)
Utility functions for:
- Image EXIF data extraction (GPS coordinates)

## Setup

### Prerequisites

- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed
- Python 3.10

### Deployment Steps

1. **Create S3 Bucket for Artifacts**:
   ```sh
   ./1-create-bucket.sh
   ```

2. **Build Lambda Layer**:
   ```sh
   ./2-build-layer.sh
   ```
   This installs dependencies from `function/requirements.txt` into the `package/` directory.

3. **Deploy Application**:
   ```sh
   ./3-deploy.sh
   ```
   This packages and deploys the application using AWS SAM.

4. **Invoke/Test Functions** (optional):
   ```sh
   ./4-invoke.sh
   ```

5. **Cleanup** (when done):
   ```sh
   ./5-cleanup.sh
   ```

### Environment Variables

Set the following environment variables in your Lambda function configuration:

- `BUCKET_NAME`: S3 bucket name for storing cafe photos
- `JWT_SECRET`: Secret key for JWT token signing (defaults to "supersecret" if not set)

### Local Development

For local development, install dependencies:

```sh
pip install -r requirements.txt
```

Note: The `requirements.txt` in the root includes additional dependencies for local development (like Streamlit), while `function/requirements.txt` contains only the Lambda function dependencies.

## Usage

### Frontend

The HTML files (`index.html`, `add.html`, `map.html`) provide a web interface for:
- Viewing uploaded cafe photos
- Adding new cafe entries with photos
- Viewing cafes on an interactive map

These files are designed to be served via GitHub Pages and communicate with the deployed Lambda functions.


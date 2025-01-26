# AWS Lambda Google Maps Integration

This project demonstrates how to integrate Google Maps API with AWS Lambda to fetch Place IDs and photos for a list of cafes in NYC. The project also includes functionality to download a CSV file from Dropbox and upload photos to an S3 bucket.

## Project Structure

- `aws-lambda-google-maps/`
  - `createlambdalayer.sh`: Script to create a Lambda layer with required dependencies.
  - `buildpackage.sh`: Script to package the Lambda function.
  - `src/`
    - `utils.py`: Utility functions for interacting with Google Maps API and Dropbox.
    - `handler.py`: Lambda function handler.
  - `requirements.txt`: List of Python dependencies.
  - `README.md`: Project documentation (this file).

## Setup

1. **Install Dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

2. **Create Lambda Layer**:
   ```sh
   ./createlambdalayer.sh 3.9
   ```

3. **Build Lambda Package**:
   ```sh
   ./buildpackage.sh
   ```

4. **Set Environment Variables**:
   Create a `.env` file with the following content:
   ```env
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key
   DROPBOX_ACCESS_TOKEN=your_dropbox_access_token
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   ```

## Usage

### Lambda Function

The Lambda function (`handler.py`) fetches Place IDs and photos for cafes listed in a CSV file stored in Dropbox. The photos are then uploaded to an S3 bucket.

### Local Testing

You can test the functionality locally by running the `lol.py` script:
```sh
python lol.py
```

### HTML Gallery

The `cafe-gallery.html` file provides a simple web interface to view the uploaded cafe photos from the S3 bucket.

## License

This project is licensed under the MIT License.
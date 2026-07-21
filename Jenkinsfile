pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        TEST_IMAGE = "market-backend-test:${BUILD_NUMBER}"
    }

    stages {
        stage('Build test image') {
            steps {
                sh 'docker build --target development -t "$TEST_IMAGE" .'
            }
        }

        stage('Quality') {
            parallel {
                stage('Ruff') {
                    steps {
                        sh 'docker run --rm "$TEST_IMAGE" uv run ruff check app tests alembic'
                    }
                }
                stage('Mypy') {
                    steps {
                        sh 'docker run --rm "$TEST_IMAGE" uv run mypy app'
                    }
                }
                stage('Tests') {
                    steps {
                        sh 'docker run --rm "$TEST_IMAGE" uv run pytest -q'
                    }
                }
            }
        }

        stage('Build production image') {
            steps {
                sh 'docker compose build api'
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                sh 'docker compose up -d --remove-orphans'
                sh 'docker compose ps'
            }
        }
    }

    post {
        always {
            sh 'docker image rm -f "$TEST_IMAGE" || true'
        }
    }
}
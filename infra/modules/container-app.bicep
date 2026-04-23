param location string
param resourceToken string
param tags object
param containerImage string
param environmentId string
param voiceLiveEndpoint string
param storageEndpoint string
param voiceLiveModel string
param voiceLiveVoice string
param openaiEndpoint string
param openaiDeployment string
param acrLoginServer string
param acrName string

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'labbuddy-${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'app' })
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acrLoginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'labbuddy'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'AZURE_VOICELIVE_ENDPOINT', value: voiceLiveEndpoint }
            { name: 'AZURE_STORAGE_ENDPOINT', value: storageEndpoint }
            { name: 'VOICELIVE_MODEL', value: voiceLiveModel }
            { name: 'VOICELIVE_VOICE', value: voiceLiveVoice }
            { name: 'AZURE_OPENAI_ENDPOINT', value: openaiEndpoint }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: openaiDeployment }
            { name: 'USE_MANAGED_IDENTITY', value: 'true' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: { metadata: { concurrentRequests: '20' } }
          }
        ]
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output identityPrincipalId string = containerApp.identity.principalId

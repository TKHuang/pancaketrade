const zerorpc = require('zerorpc')

const client = new zerorpc.Client()

client.connect('tcp://127.0.0.1:4242')

const tokenAddress = document.querySelector('#addToken')
const result = document.querySelector('#result')

tokenAddress.addEventListener('input', () => {
  client.invoke('', tokenAddress.value, (error, res) => {
    if (error) {
      console.error(error)
    } else {
      result.textContent = res
    }
  })
})

tokenAddress.dispatchEvent(new Event('input'))

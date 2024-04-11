package main

import (
	"bufio"
	"context"
	"fmt"
	"os"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/cognitoidentityprovider"
	ddTypes "github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	cdTypes "github.com/aws/aws-sdk-go-v2/service/cognitoidentityprovider/types"

)


func main() {
    cfg, err := config.LoadDefaultConfig(context.TODO())
    if err != nil {
        fmt.Printf("Error loading configuration: %v\n", err)
        return
    }
    
    // You can also try to retrieve credentials to show them, but be careful with sensitive data!
    creds, err := cfg.Credentials.Retrieve(context.TODO())
    if err != nil {
        fmt.Printf("Error retrieving credentials: %v\n", err)
    } else {
        fmt.Printf("Access Key ID: %s\n", creds.AccessKeyID)
        // Never print the secret access key or session token in a production environment
    }

    svc := cognitoidentityprovider.NewFromConfig(cfg)

    reader := bufio.NewReader(os.Stdin)
    fmt.Print("Enter Username: ")
    username, _ := reader.ReadString('\n')
    fmt.Print("Enter Password: ")
    password, _ := reader.ReadString('\n')

    username = username[:len(username)-1]
    password = password[:len(password)-1]

    accessToken, err := cognitoLogin(username, password, svc)

	userId := getUserIdFromLogin(svc, accessToken)
    if err != nil {
        fmt.Printf("error retrieving user info: %v\n", err)
        return
    }

	fmt.Println("user id:", userId)

    // Call GetUser with the access token
    userAgents, err := getAgentByUserId(userId)
    if err != nil {
        fmt.Printf("error retrieving user info: %v\n", err)
        return
    }

    // Print user attributes in a readable format
    fmt.Println("User Attributes:")
	fmt.Println(userAgents)


}

func getAgentByUserId(userId string) ([]string, error) {
    // Load the AWS Configuration
    cfg, err := config.LoadDefaultConfig(context.TODO(),
        config.WithRegion("us-east-1"),
    )
    if err != nil {
        return nil, fmt.Errorf("unable to load SDK config, %v", err)
    }

    // Create a DynamoDB client
    svc := dynamodb.NewFromConfig(cfg)

    // Define the query input using the newly created index
    queryInput := &dynamodb.QueryInput{
        TableName: aws.String("CreateAgent-uq5dutwsirgtjemnq5shgxsoai-staging"), // Replace with your table name
        IndexName: aws.String("userId-index"), // Use the index you created
        KeyConditionExpression: aws.String("userId = :v1"),
        ExpressionAttributeValues: map[string]ddTypes.AttributeValue{
            ":v1": &ddTypes.AttributeValueMemberS{Value: userId}, // Use the userId value passed to the function
        },
    }

    // Execute the query
    result, err := svc.Query(context.TODO(), queryInput)
    if err != nil {
        return nil, fmt.Errorf("Query API call failed: %v", err)
    }

    // Extract the 'AgentName' from each item in the results
    var agentNames []string
    for _, item := range result.Items {
        if agentNameValue, ok := item["AgentName"].(*ddTypes.AttributeValueMemberS); ok {
            agentNames = append(agentNames, agentNameValue.Value)
        } else {
            // Optionally handle the case where AgentName is missing or not a string
            // For example, you could append "Unknown" or log a warning
            agentNames = append(agentNames, "Unknown")
        }
    }

    return agentNames, nil
}






func getUserIdFromLogin(svc *cognitoidentityprovider.Client, accessToken string) (string) {
    input := &cognitoidentityprovider.GetUserInput{
        AccessToken: &accessToken,
    }

    userInfo, err := svc.GetUser(context.TODO(), input)

	if err != nil{
		fmt.Println("error here")
	}

	userId := ""

    for _, attribute := range userInfo.UserAttributes {
        // fmt.Printf("  %s: %s\n", *attribute.Name, *attribute.Value)
        if *attribute.Name == "sub" {
            userId = *attribute.Value
        }
    }

	return userId
}


func cognitoLogin(username string, password string, svc*cognitoidentityprovider.Client) (string, error){
	params := &cognitoidentityprovider.InitiateAuthInput{
        AuthFlow: cdTypes.AuthFlowTypeUserPasswordAuth,
        AuthParameters: map[string]string{
            "USERNAME": username,
            "PASSWORD": password,
        },
        ClientId: aws.String("66pf7gqb8jdnt414ldgfmtj4d6"),  // Replace with your actual client ID
    }

    resp, err := svc.InitiateAuth(context.TODO(), params)
    if err != nil {
        fmt.Printf("authentication failed: %v\n", err)
    }

    accessToken := *resp.AuthenticationResult.AccessToken
    fmt.Printf("Authentication successful, access token: %s\n", accessToken)

	return accessToken, err
}
